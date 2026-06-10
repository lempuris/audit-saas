import { SignIn } from "@clerk/clerk-react";

export default function SignInScreen() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-slate-100">
      <h1 className="text-2xl font-semibold text-slate-800">AuditSaaS</h1>
      <SignIn />
    </main>
  );
}
