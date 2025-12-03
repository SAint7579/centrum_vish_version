import Link from "next/link";
import { Heart, MessageCircle, Sparkles, ArrowRight, Users, Shield } from "lucide-react";

export default function Home() {
  return (
    <main className="gradient-bg min-h-screen">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 glass">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-rose-500 to-rose-600 flex items-center justify-center">
              <Heart className="w-4 h-4 text-white fill-white" />
            </div>
            <span className="font-serif font-semibold text-xl tracking-tight">Centrum</span>
          </div>
          <div className="flex items-center gap-4">
            <Link 
              href="/auth/login"
              className="text-stone-400 hover:text-white transition-colors"
            >
              Sign In
            </Link>
            <Link 
              href="/auth/signup"
              className="px-4 py-2 rounded-full bg-gradient-to-r from-rose-500 to-rose-600 text-white font-medium hover:opacity-90 transition-opacity"
            >
              Find Love
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass text-sm text-stone-400 mb-8">
            <Heart className="w-4 h-4 text-rose-400 fill-rose-400" />
            Where real connections begin
          </div>
          
          <h1 className="font-serif text-5xl md:text-7xl font-medium leading-tight mb-6">
            Find Someone Who{" "}
            <span className="gradient-text italic">Gets You</span>
          </h1>
          
          <p className="text-xl text-stone-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            Skip the awkward texting. Have a real conversation and let your personality shine. 
            We'll help you connect with people who truly match your vibe.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link 
              href="/auth/signup"
              className="group px-8 py-4 rounded-full bg-gradient-to-r from-rose-500 to-rose-600 text-white font-semibold text-lg flex items-center gap-2 hover:gap-4 transition-all pulse-glow"
            >
              Start Your Journey
              <ArrowRight className="w-5 h-5 transition-transform group-hover:translate-x-1" />
            </Link>
            <Link 
              href="/auth/login"
              className="px-8 py-4 rounded-full glass text-white font-semibold text-lg hover:bg-stone-800/50 transition-colors"
            >
              Welcome Back
            </Link>
          </div>

          {/* Stats */}
          <div className="mt-16 flex items-center justify-center gap-12 text-center">
            <div>
              <div className="text-3xl font-serif font-semibold text-white">10K+</div>
              <div className="text-sm text-stone-500">Active Members</div>
            </div>
            <div className="w-px h-12 bg-stone-800"></div>
            <div>
              <div className="text-3xl font-serif font-semibold text-white">2.5K</div>
              <div className="text-sm text-stone-500">Matches Made</div>
            </div>
            <div className="w-px h-12 bg-stone-800"></div>
            <div>
              <div className="text-3xl font-serif font-semibold text-white">94%</div>
              <div className="text-sm text-stone-500">Happy Dates</div>
            </div>
          </div>
        </div>
      </section>

      {/* How it Works */}
      <section className="py-20 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="font-serif text-3xl md:text-4xl font-medium mb-4">
              Dating, Reimagined
            </h2>
            <p className="text-stone-400 max-w-xl mx-auto">
              Forget swiping through endless photos. Get to know someone through 
              real conversation first.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <FeatureCard 
              icon={<MessageCircle className="w-6 h-6" />}
              step="01"
              title="Have a Conversation"
              description="Chat naturally with our friendly AI to create your profile. No forms, no pressure — just be yourself."
            />
            <FeatureCard 
              icon={<Heart className="w-6 h-6" />}
              step="02"
              title="Get Matched"
              description="We pair you with people who share your interests, values, and sense of humor. Quality over quantity."
            />
            <FeatureCard 
              icon={<Users className="w-6 h-6" />}
              step="03"
              title="Connect Authentically"
              description="Start meaningful conversations with your matches. Your personality leads, not just your photos."
            />
          </div>
        </div>
      </section>

      {/* Why Different */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="glass rounded-3xl p-10 md:p-14 soft-glow">
            <div className="text-center mb-10">
              <h2 className="font-serif text-3xl md:text-4xl font-medium mb-4">
                Why People Love Centrum
              </h2>
            </div>
            
            <div className="grid md:grid-cols-2 gap-8">
              <Testimonial 
                quote="Finally, a dating app that lets me show who I really am before judging by looks alone."
                name="Sarah, 28"
              />
              <Testimonial 
                quote="I met my girlfriend here. We connected over our shared love of terrible puns first!"
                name="Mike, 32"
              />
            </div>

            <div className="mt-10 pt-10 border-t border-stone-800 flex flex-wrap items-center justify-center gap-8">
              <div className="flex items-center gap-2 text-stone-400">
                <Shield className="w-5 h-5 text-rose-400" />
                <span>Verified Profiles</span>
              </div>
              <div className="flex items-center gap-2 text-stone-400">
                <Heart className="w-5 h-5 text-rose-400" />
                <span>Personality First</span>
              </div>
              <div className="flex items-center gap-2 text-stone-400">
                <Sparkles className="w-5 h-5 text-rose-400" />
                <span>AI-Powered Matching</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-6">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="font-serif text-3xl md:text-4xl font-medium mb-4">
            Ready to Meet Your Person?
          </h2>
          <p className="text-stone-400 mb-8">
            Join thousands of singles who are tired of superficial dating apps.
          </p>
          <Link 
            href="/auth/signup"
            className="inline-flex items-center gap-2 px-8 py-4 rounded-full bg-gradient-to-r from-rose-500 to-rose-600 text-white font-semibold text-lg hover:opacity-90 transition-opacity"
          >
            Create Free Profile
            <Heart className="w-5 h-5 fill-white" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-stone-800">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Heart className="w-4 h-4 text-rose-400 fill-rose-400" />
            <span className="font-serif">Centrum</span>
          </div>
          <div className="text-stone-500 text-sm">
            © 2024 Centrum. Made with love.
          </div>
          <div className="flex items-center gap-6 text-sm text-stone-500">
            <a href="#" className="hover:text-white transition-colors">Privacy</a>
            <a href="#" className="hover:text-white transition-colors">Terms</a>
            <a href="#" className="hover:text-white transition-colors">Contact</a>
          </div>
        </div>
      </footer>
    </main>
  );
}

function FeatureCard({ icon, step, title, description }: { 
  icon: React.ReactNode;
  step: string;
  title: string; 
  description: string;
}) {
  return (
    <div className="glass rounded-2xl p-8 hover:border-rose-500/20 transition-colors relative">
      <div className="absolute top-6 right-6 text-4xl font-serif text-stone-800">{step}</div>
      <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-rose-500/20 to-rose-600/20 flex items-center justify-center text-rose-400 mb-4">
        {icon}
      </div>
      <h3 className="font-serif font-medium text-xl mb-2">{title}</h3>
      <p className="text-stone-400">{description}</p>
    </div>
  );
}

function Testimonial({ quote, name }: { quote: string; name: string }) {
  return (
    <div className="text-left">
      <p className="text-lg text-stone-300 italic mb-4">"{quote}"</p>
      <p className="text-rose-400 font-medium">{name}</p>
    </div>
  );
}
