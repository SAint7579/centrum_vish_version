'use client';

import { useState, useEffect, useRef } from 'react';
import { createClient } from '@/lib/supabase/client';
import { useRouter } from 'next/navigation';
import { Heart, Mic, MicOff, Phone, PhoneOff, Loader2, Volume2, User } from 'lucide-react';
import Link from 'next/link';

interface ProfileData {
  age?: number;
  about_me?: string;
  looking_for?: string;
}

type ConversationStatus = 'idle' | 'connecting' | 'active' | 'ending' | 'completed' | 'error';

export default function OnboardingPage() {
  const [status, setStatus] = useState<ConversationStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const [profile, setProfile] = useState<ProfileData>({});
  const [transcript, setTranscript] = useState<{role: string; content: string}[]>([]);
  const [isMuted, setIsMuted] = useState(false);
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const captureContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const statusRef = useRef<ConversationStatus>('idle');
  const isMutedRef = useRef(false);
  
  // Audio queue for sequential playback
  const audioQueueRef = useRef<Float32Array[]>([]);
  const isPlayingRef = useRef(false);
  const nextPlayTimeRef = useRef(0);
  
  const router = useRouter();
  const supabase = createClient();

  // Keep refs in sync
  useEffect(() => {
    statusRef.current = status;
  }, [status]);

  useEffect(() => {
    isMutedRef.current = isMuted;
  }, [isMuted]);

  // Check auth on mount
  useEffect(() => {
    const checkUser = async () => {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) {
        router.push('/auth/login');
        return;
      }
      setUserId(user.id);
    };
    checkUser();
  }, [supabase, router]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanupAudio();
    };
  }, []);

  const cleanupAudio = () => {
    console.log('Cleaning up audio...');
    
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (sourceRef.current) {
      sourceRef.current.disconnect();
      sourceRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }
    if (captureContextRef.current && captureContextRef.current.state !== 'closed') {
      captureContextRef.current.close();
      captureContextRef.current = null;
    }
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  };

  const startConversation = async () => {
    if (!userId) return;
    
    setStatus('connecting');
    setError(null);
    setTranscript([]);
    setProfile({});

    try {
      // Request microphone access
      console.log('Requesting microphone...');
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        } 
      });
      mediaStreamRef.current = stream;
      console.log('Microphone access granted');

      // Initialize audio context for playback
      audioContextRef.current = new AudioContext();
      if (audioContextRef.current.state === 'suspended') {
        await audioContextRef.current.resume();
      }
      console.log('Playback audio context ready');

      // Initialize capture context at 16kHz
      captureContextRef.current = new AudioContext({ sampleRate: 16000 });
      console.log('Capture audio context ready');

      // Start conversation session
      console.log('Starting conversation session...');
      const response = await fetch('http://localhost:8000/api/conversation/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId }),
      });

      if (!response.ok) {
        throw new Error('Failed to start conversation');
      }

      const { session_id, websocket_url } = await response.json();
      console.log('Session started:', session_id);

      // Connect to WebSocket
      const ws = new WebSocket(`ws://localhost:8000${websocket_url}`);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected, setting up audio capture...');
        setupAudioCapture(ws);
      };

      ws.onmessage = async (event) => {
        if (event.data instanceof Blob) {
          console.log('Received audio blob:', event.data.size, 'bytes');
          await playAudioChunk(event.data);
        } else {
          try {
            const msg = JSON.parse(event.data);
            handleMessage(msg);
          } catch (e) {
            console.log('Non-JSON message:', event.data);
          }
        }
      };

      ws.onerror = (err) => {
        console.error('WebSocket error:', err);
        setError('Connection error. Is the backend running?');
        setStatus('error');
      };

      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason, 'status was:', statusRef.current);
        if (statusRef.current === 'ending' || statusRef.current === 'active') {
          setStatus('completed');
        }
      };

    } catch (err: any) {
      console.error('Error starting conversation:', err);
      setError(err.message || 'Failed to start conversation');
      setStatus('error');
    }
  };

  const setupAudioCapture = (ws: WebSocket) => {
    if (!captureContextRef.current || !mediaStreamRef.current) {
      console.error('Missing capture context or media stream');
      return;
    }

    console.log('Setting up audio capture pipeline...');
    
    const source = captureContextRef.current.createMediaStreamSource(mediaStreamRef.current);
    sourceRef.current = source;
    
    const processor = captureContextRef.current.createScriptProcessor(4096, 1, 1);
    processorRef.current = processor;

    let chunkCount = 0;
    processor.onaudioprocess = (e) => {
      const wsOpen = ws.readyState === WebSocket.OPEN;
      const notMuted = !isMutedRef.current;
      
      if (!wsOpen) {
        if (chunkCount % 100 === 0) console.log('⚠️ WebSocket not open');
        return;
      }
      
      if (!notMuted) {
        if (chunkCount % 100 === 0) console.log('🔇 Muted, not sending');
        return;
      }
      
      const inputData = e.inputBuffer.getChannelData(0);
      const pcmData = new Int16Array(inputData.length);
      
      // Convert and check audio level
      let maxVal = 0;
      for (let i = 0; i < inputData.length; i++) {
        pcmData[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
        maxVal = Math.max(maxVal, Math.abs(inputData[i]));
      }
      
      // Always send audio (let Eleven Labs handle silence detection)
      ws.send(pcmData.buffer);
      chunkCount++;
      
      // Log every 25 chunks (~1 second at 4096 samples / 16kHz)
      if (chunkCount % 25 === 1) {
        const level = maxVal > 0.1 ? '🔊' : maxVal > 0.01 ? '🔉' : '🔈';
        console.log(`${level} Audio #${chunkCount}, level: ${(maxVal * 100).toFixed(1)}%`);
      }
    };

    source.connect(processor);
    processor.connect(captureContextRef.current.destination);
    console.log('Audio capture pipeline connected');
  };

  const playAudioChunk = async (blob: Blob) => {
    if (!audioContextRef.current) {
      console.log('No audio context for playback');
      return;
    }
    
    if (audioContextRef.current.state === 'suspended') {
      await audioContextRef.current.resume();
    }
    
    try {
      const arrayBuffer = await blob.arrayBuffer();
      
      // Eleven Labs sends PCM 16-bit 16kHz mono audio
      const pcmData = new Int16Array(arrayBuffer);
      const floatData = new Float32Array(pcmData.length);
      
      // Convert Int16 to Float32 (-1.0 to 1.0)
      for (let i = 0; i < pcmData.length; i++) {
        floatData[i] = pcmData[i] / 32768.0;
      }
      
      // Schedule this chunk to play after previous ones
      const ctx = audioContextRef.current;
      const audioBuffer = ctx.createBuffer(1, floatData.length, 16000);
      audioBuffer.getChannelData(0).set(floatData);
      
      const source = ctx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(ctx.destination);
      
      // Calculate when to start this chunk
      const now = ctx.currentTime;
      const startTime = Math.max(now, nextPlayTimeRef.current);
      const duration = audioBuffer.duration;
      
      // Update next play time
      nextPlayTimeRef.current = startTime + duration;
      
      // Schedule playback
      source.start(startTime);
      
      // Track speaking state
      if (!isPlayingRef.current) {
        isPlayingRef.current = true;
        setIsAgentSpeaking(true);
      }
      
      source.onended = () => {
        // Check if this was the last scheduled chunk
        if (ctx.currentTime >= nextPlayTimeRef.current - 0.1) {
          isPlayingRef.current = false;
          setIsAgentSpeaking(false);
        }
      };
      
    } catch (err) {
      console.error('Error playing audio:', err);
      setIsAgentSpeaking(false);
    }
  };

  const handleMessage = (msg: any) => {
    console.log('Received message:', msg.type);
    
    switch (msg.type) {
      case 'ready':
        setStatus('active');
        console.log('Conversation is now active');
        break;
        
      case 'user_transcript':
        if (msg.user_transcript) {
          setTranscript(prev => [...prev, { role: 'user', content: msg.user_transcript }]);
        }
        break;
        
      case 'agent_response':
        if (msg.agent_response) {
          setTranscript(prev => [...prev, { role: 'agent', content: msg.agent_response }]);
        }
        break;
        
      case 'profile_updated':
        if (msg.profile) {
          setProfile(msg.profile);
        }
        break;
        
      case 'session_ended':
        setStatus('completed');
        setProfile(msg.profile || {});
        break;
        
      case 'error':
        setError(msg.message);
        setStatus('error');
        break;
        
      case 'conversation_initiation_metadata_event':
        console.log('Conversation initiated with Eleven Labs');
        break;
        
      default:
        console.log('Unknown message type:', msg.type);
    }
  };

  const stopConversation = () => {
    console.log('Stopping conversation...');
    setStatus('ending');
    
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'end_conversation' }));
      wsRef.current.close();
    }
    
    cleanupAudio();
  };

  const toggleMute = () => {
    setIsMuted(!isMuted);
    console.log('Mute toggled:', !isMuted);
  };

  const goToDashboard = () => {
    router.push('/dashboard');
  };

  const retryConversation = () => {
    cleanupAudio();
    setStatus('idle');
    setError(null);
  };

  return (
    <main className="gradient-bg min-h-screen">
      {/* Header */}
      <nav className="fixed top-0 left-0 right-0 z-50 glass">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/dashboard" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-rose-500 to-rose-600 flex items-center justify-center">
              <Heart className="w-4 h-4 text-white fill-white" />
            </div>
            <span className="font-serif font-semibold text-xl">Centrum</span>
          </Link>
        </div>
      </nav>

      <div className="pt-24 px-6 pb-12">
        <div className="max-w-4xl mx-auto">
          {/* Title */}
          <div className="text-center mb-8">
            <h1 className="font-serif text-3xl font-medium mb-2">
              {status === 'completed' ? 'Profile Created! 🎉' : 'Create Your Profile'}
            </h1>
            <p className="text-stone-400">
              {status === 'idle' && "Click the button below to start a voice chat"}
              {status === 'connecting' && "Setting up your conversation..."}
              {status === 'active' && "Just talk naturally - I'm listening!"}
              {status === 'ending' && "Wrapping up and saving your profile..."}
              {status === 'completed' && "Your profile has been created from our conversation"}
              {status === 'error' && "Something went wrong"}
            </p>
          </div>

          {/* Main Content */}
          <div className="grid md:grid-cols-2 gap-6">
            {/* Conversation Panel */}
            <div className="glass rounded-2xl p-6">
              <h2 className="font-medium mb-4 flex items-center gap-2">
                <Volume2 className={`w-5 h-5 ${isAgentSpeaking ? 'text-rose-400 animate-pulse' : 'text-stone-500'}`} />
                Conversation
              </h2>
              
              {/* Transcript */}
              <div className="h-80 overflow-y-auto mb-4 space-y-3">
                {status === 'idle' && (
                  <p className="text-stone-500 text-center py-8">
                    Press "Start Chat" to begin
                  </p>
                )}
                {status === 'connecting' && (
                  <p className="text-stone-500 text-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                    Connecting to agent...
                  </p>
                )}
                {transcript.length === 0 && status === 'active' && (
                  <p className="text-stone-500 text-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                    Waiting for agent...
                  </p>
                )}
                {transcript.map((msg, i) => (
                  <div 
                    key={i} 
                    className={`p-3 rounded-xl ${
                      msg.role === 'user' 
                        ? 'bg-rose-500/10 ml-8' 
                        : 'bg-stone-800/50 mr-8'
                    }`}
                  >
                    <p className="text-xs text-stone-500 mb-1">
                      {msg.role === 'user' ? 'You' : 'Centrum'}
                    </p>
                    <p className="text-sm">{msg.content}</p>
                  </div>
                ))}
              </div>

              {/* Controls */}
              <div className="flex items-center justify-center gap-4">
                {status === 'idle' && (
                  <button
                    onClick={startConversation}
                    disabled={!userId}
                    className="flex items-center gap-2 px-6 py-3 rounded-full bg-gradient-to-r from-rose-500 to-rose-600 text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
                  >
                    <Phone className="w-5 h-5" />
                    Start Chat
                  </button>
                )}

                {status === 'connecting' && (
                  <div className="flex items-center gap-2 text-stone-400">
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Connecting...
                  </div>
                )}
                
                {status === 'active' && (
                  <>
                    <button
                      onClick={toggleMute}
                      className={`p-4 rounded-full transition-colors ${
                        isMuted 
                          ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30' 
                          : 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
                      }`}
                    >
                      {isMuted ? <MicOff className="w-6 h-6" /> : <Mic className="w-6 h-6" />}
                    </button>
                    <button
                      onClick={stopConversation}
                      className="p-4 rounded-full bg-red-500 text-white hover:bg-red-600 transition-colors"
                    >
                      <PhoneOff className="w-6 h-6" />
                    </button>
                  </>
                )}
                
                {status === 'ending' && (
                  <div className="flex items-center gap-2 text-stone-400">
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Saving profile...
                  </div>
                )}
                
                {status === 'completed' && (
                  <button
                    onClick={goToDashboard}
                    className="flex items-center gap-2 px-6 py-3 rounded-full bg-gradient-to-r from-rose-500 to-rose-600 text-white font-medium"
                  >
                    <Heart className="w-5 h-5 fill-white" />
                    View My Profile
                  </button>
                )}
                
                {status === 'error' && (
                  <button
                    onClick={retryConversation}
                    className="flex items-center gap-2 px-6 py-3 rounded-full bg-stone-800 text-white font-medium"
                  >
                    Try Again
                  </button>
                )}
              </div>

              {error && (
                <p className="text-red-400 text-sm text-center mt-4">{error}</p>
              )}
              
              {status === 'active' && isMuted && (
                <p className="text-amber-400 text-xs text-center mt-4">
                  🎤 You're muted. Click the mic button to speak.
                </p>
              )}
            </div>

            {/* Profile Preview Panel */}
            <div className="glass rounded-2xl p-6">
              <h2 className="font-medium mb-4 flex items-center gap-2">
                <User className="w-5 h-5 text-rose-400" />
                Your Profile
              </h2>
              
              <div className="space-y-4">
                <ProfileField label="Name" value={profile.name} />
                <ProfileField label="Age" value={profile.age?.toString()} />
                <ProfileField label="Location" value={profile.location} />
                <ProfileField label="Occupation" value={profile.occupation} />
                <ProfileField 
                  label="Interests" 
                  value={profile.interests?.join(', ')} 
                />
                <ProfileField label="Looking for" value={profile.looking_for} />
                <ProfileField label="About" value={profile.about_me} />
                <ProfileField label="Ideal Partner" value={profile.ideal_partner} />
                {profile.fun_facts && profile.fun_facts.length > 0 && (
                  <ProfileField 
                    label="Fun Facts" 
                    value={profile.fun_facts.join(' • ')} 
                  />
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

function ProfileField({ label, value }: { label: string; value?: string }) {
  return (
    <div>
      <p className="text-xs text-stone-500 mb-1">{label}</p>
      <p className={`text-sm ${value ? 'text-white' : 'text-stone-600 italic'}`}>
        {value || 'Not yet shared'}
      </p>
    </div>
  );
}
