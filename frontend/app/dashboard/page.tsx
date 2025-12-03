import { createClient } from '@/lib/supabase/server';
import { redirect } from 'next/navigation';
import { Heart, MessageCircle, User, LogOut, Sparkles } from 'lucide-react';
import Link from 'next/link';

export default async function DashboardPage() {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) {
    redirect('/auth/login');
  }

  return (
    <main className="gradient-bg min-h-screen">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 glass">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-rose-500 to-rose-600 flex items-center justify-center">
              <Heart className="w-4 h-4 text-white fill-white" />
            </div>
            <span className="font-serif font-semibold text-xl">Centrum</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-stone-400 text-sm">
              {user.email}
            </span>
            <form action="/auth/signout" method="post">
              <button 
                type="submit"
                className="p-2 rounded-lg hover:bg-stone-800/50 text-stone-400 hover:text-white transition-colors"
              >
                <LogOut className="w-5 h-5" />
              </button>
            </form>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="pt-24 px-6 pb-12">
        <div className="max-w-4xl mx-auto">
          {/* Welcome */}
          <div className="mb-12">
            <h1 className="font-serif text-3xl font-medium mb-2">
              Hey {user.user_metadata?.full_name || 'there'}! 💕
            </h1>
            <p className="text-stone-400">
              Ready to create your profile and start meeting amazing people?
            </p>
          </div>

          {/* Action Cards */}
          <div className="grid md:grid-cols-2 gap-6">
            {/* Create Profile Card */}
            <div className="glass rounded-2xl p-8 hover:border-rose-500/20 transition-colors group">
              <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-rose-500/20 to-rose-600/20 flex items-center justify-center text-rose-400 mb-6 group-hover:scale-110 transition-transform">
                <MessageCircle className="w-7 h-7" />
              </div>
              <h2 className="font-serif text-xl font-medium mb-2">Create Your Profile</h2>
              <p className="text-stone-400 mb-6">
                Have a quick chat with us to build your dating profile. No boring forms — just be yourself!
              </p>
              <Link
                href="/onboarding"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-gradient-to-r from-rose-500 to-rose-600 text-white font-medium hover:opacity-90 transition-opacity"
              >
                <Sparkles className="w-5 h-5" />
                Let's Chat
              </Link>
            </div>

            {/* Browse Matches Card */}
            <div className="glass rounded-2xl p-8 hover:border-rose-500/20 transition-colors group opacity-50">
              <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-rose-500/20 to-rose-600/20 flex items-center justify-center text-rose-400 mb-6">
                <Heart className="w-7 h-7" />
              </div>
              <h2 className="font-serif text-xl font-medium mb-2">Browse Matches</h2>
              <p className="text-stone-400 mb-6">
                See people who match your vibe and start meaningful conversations.
              </p>
              <button
                disabled
                className="inline-flex items-center gap-2 px-6 py-3 rounded-full glass border border-stone-700 text-stone-500 font-medium cursor-not-allowed"
              >
                <Heart className="w-5 h-5" />
                Complete Profile First
              </button>
            </div>
          </div>

          {/* Progress */}
          <div className="mt-12 glass rounded-xl p-6">
            <h3 className="font-medium mb-4">Your Journey</h3>
            <div className="space-y-3">
              <ProgressItem 
                label="Account Created" 
                completed={true} 
              />
              <ProgressItem 
                label="Dating Profile" 
                completed={false} 
              />
              <ProgressItem 
                label="First Match" 
                completed={false} 
              />
              <ProgressItem 
                label="First Conversation" 
                completed={false} 
              />
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

function ProgressItem({ label, completed }: { label: string; completed: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <div className={`w-6 h-6 rounded-full flex items-center justify-center ${
        completed 
          ? 'bg-rose-500/20 text-rose-400' 
          : 'bg-stone-800 text-stone-600'
      }`}>
        {completed ? (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        ) : (
          <div className="w-2 h-2 rounded-full bg-current" />
        )}
      </div>
      <span className={completed ? 'text-white' : 'text-stone-500'}>{label}</span>
    </div>
  );
}
