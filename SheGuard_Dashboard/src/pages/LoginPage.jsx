import { useState } from 'react';
import { ShieldCheck } from 'lucide-react';
import { login, setToken } from '../services/api';

export default function LoginPage({ onSuccess }) {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      await login(phoneNumber.trim(), password);
      onSuccess?.();
    } catch (err) {
      setError(err?.message || 'Login failed. Check your phone number and password.');
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-command px-4 text-white">
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute left-1/2 top-[-18rem] h-[38rem] w-[38rem] -translate-x-1/2 rounded-full bg-alert-500/14 blur-3xl" />
      </div>
      <div className="relative w-full max-w-md rounded-[1.7rem] border border-white/10 bg-white/[0.055] p-8 shadow-panel backdrop-blur-2xl">
        <div className="mb-8 flex flex-col items-center gap-3 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-alert-500/40 bg-alert-500/14 shadow-glow">
            <ShieldCheck className="h-8 w-8 text-alert-500" />
          </div>
          <div>
            <h1 className="text-3xl font-black tracking-tight">SheGuard Desk</h1>
            <p className="mt-1 text-sm text-slate-400">Sign in to the live emergency monitor</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="grid gap-4">
          <label className="grid gap-2 text-sm font-semibold text-slate-300">
            Phone number
            <input
              type="tel"
              required
              value={phoneNumber}
              onChange={(event) => setPhoneNumber(event.target.value)}
              placeholder="10-digit mobile number"
              className="h-12 rounded-xl border border-white/10 bg-white/[0.055] px-4 text-white outline-none transition focus:border-alert-500/50 placeholder:text-slate-500"
            />
          </label>
          <label className="grid gap-2 text-sm font-semibold text-slate-300">
            Password
            <input
              type="password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="••••••••"
              className="h-12 rounded-xl border border-white/10 bg-white/[0.055] px-4 text-white outline-none transition focus:border-alert-500/50 placeholder:text-slate-500"
            />
          </label>

          {error && (
            <p className="rounded-xl border border-alert-500/30 bg-alert-500/12 px-4 py-3 text-sm text-red-100">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="mt-2 flex h-12 items-center justify-center rounded-xl bg-alert-500 text-sm font-black uppercase tracking-[0.14em] text-white transition hover:bg-alert-600 disabled:opacity-60"
          >
            {isLoading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </main>
  );
}
