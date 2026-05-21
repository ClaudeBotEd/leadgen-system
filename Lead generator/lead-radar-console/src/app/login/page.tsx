import { signIn } from '@/../auth';

export default function LoginPage() {
  async function loginAction(formData: FormData) {
    'use server';
    const email = formData.get('email') as string;
    await signIn('resend', { email, redirectTo: '/triage' });
  }
  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-950 text-zinc-100 font-mono">
      <div className="w-full max-w-sm p-8 border border-zinc-800 rounded">
        <h1 className="text-lg mb-6">Lead Radar — Operator Console</h1>
        <form action={loginAction} className="space-y-4">
          <input type="email" name="email" placeholder="operator@example.com" required
            className="w-full p-2 bg-zinc-900 border border-zinc-800 rounded" />
          <button type="submit" className="w-full p-2 bg-zinc-100 text-zinc-950 rounded">
            Send magic link
          </button>
        </form>
      </div>
    </main>
  );
}
