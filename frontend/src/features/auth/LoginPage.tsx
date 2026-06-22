import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod/v4';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/auth/useAuth';

const loginSchema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(1, 'Password is required'),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [serverError, setServerError] = useState<string | null>(null);
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  const returnPath = (location.state as { from?: string } | null)?.from ?? '/dashboard';

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      username: '',
      password: '',
    },
  });

  const onSubmit = async (data: LoginFormValues) => {
    setServerError(null);
    setIsLoggingIn(true);
    try {
      await login(data.username, data.password);
      // Brief delay for the vessel animation to play
      setTimeout(() => {
        navigate(returnPath, { replace: true });
      }, 800);
    } catch {
      setIsLoggingIn(false);
      setServerError('Invalid username or password');
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-slate-50">
      {/* Background — ocean gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-sky-100 via-blue-50 to-cyan-50" />

      {/* Subtle wave pattern overlay */}
      <div className="absolute inset-0 opacity-30">
        <svg
          className="absolute bottom-0 w-full h-64"
          viewBox="0 0 1440 320"
          preserveAspectRatio="none"
        >
          <path
            fill="#bae6fd"
            fillOpacity="0.4"
            d="M0,224L48,213.3C96,203,192,181,288,181.3C384,181,480,203,576,218.7C672,235,768,245,864,234.7C960,224,1056,192,1152,176C1248,160,1344,160,1392,160L1440,160L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"
          />
          <path
            fill="#7dd3fc"
            fillOpacity="0.2"
            d="M0,288L48,272C96,256,192,224,288,218.7C384,213,480,235,576,245.3C672,256,768,256,864,245.3C960,235,1056,213,1152,208C1248,203,1344,213,1392,218.7L1440,224L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"
          />
        </svg>
      </div>

      {/* Shipping containers — decorative floating elements */}
      <div className="absolute top-[15%] left-[5%] opacity-20 animate-[float_6s_ease-in-out_infinite]">
        <div className="w-20 h-12 bg-red-400 rounded-sm border border-red-500/30 flex items-center justify-center">
          <div className="w-16 h-1 bg-red-600/40 rounded" />
        </div>
      </div>
      <div className="absolute top-[25%] right-[8%] opacity-15 animate-[float_8s_ease-in-out_infinite_1s]">
        <div className="w-24 h-14 bg-blue-400 rounded-sm border border-blue-500/30 flex items-center justify-center">
          <div className="w-20 h-1 bg-blue-600/40 rounded" />
        </div>
      </div>
      <div className="absolute bottom-[30%] left-[10%] opacity-10 animate-[float_7s_ease-in-out_infinite_2s]">
        <div className="w-16 h-10 bg-emerald-400 rounded-sm border border-emerald-500/30 flex items-center justify-center">
          <div className="w-12 h-1 bg-emerald-600/40 rounded" />
        </div>
      </div>
      <div className="absolute top-[60%] right-[12%] opacity-10 animate-[float_9s_ease-in-out_infinite_0.5s]">
        <div className="w-18 h-11 bg-amber-400 rounded-sm border border-amber-500/30 flex items-center justify-center">
          <div className="w-14 h-1 bg-amber-600/40 rounded" />
        </div>
      </div>

      {/* Vessel illustration — moves forward on login */}
      <div
        className={`absolute bottom-[12%] transition-all duration-[1500ms] ease-in-out ${
          isLoggingIn
            ? 'left-[110%] opacity-0 scale-95'
            : 'left-[3%] opacity-20'
        }`}
      >
        <svg
          width="280"
          height="100"
          viewBox="0 0 280 100"
          fill="none"
          className="text-slate-600"
        >
          {/* Hull */}
          <path
            d="M20 70 L40 90 L240 90 L260 70 Z"
            fill="currentColor"
            opacity="0.3"
          />
          {/* Deck */}
          <rect x="50" y="50" width="180" height="20" rx="2" fill="currentColor" opacity="0.25" />
          {/* Bridge */}
          <rect x="180" y="25" width="40" height="25" rx="2" fill="currentColor" opacity="0.3" />
          {/* Containers on deck */}
          <rect x="60" y="35" width="25" height="15" rx="1" fill="#ef4444" opacity="0.3" />
          <rect x="88" y="35" width="25" height="15" rx="1" fill="#3b82f6" opacity="0.3" />
          <rect x="116" y="35" width="25" height="15" rx="1" fill="#10b981" opacity="0.3" />
          <rect x="144" y="35" width="25" height="15" rx="1" fill="#f59e0b" opacity="0.3" />
          {/* Stack second row */}
          <rect x="70" y="20" width="25" height="15" rx="1" fill="#8b5cf6" opacity="0.2" />
          <rect x="98" y="20" width="25" height="15" rx="1" fill="#06b6d4" opacity="0.2" />
          <rect x="126" y="20" width="25" height="15" rx="1" fill="#ec4899" opacity="0.2" />
          {/* Smokestack */}
          <rect x="195" y="12" width="10" height="13" rx="1" fill="currentColor" opacity="0.2" />
          {/* Wake */}
          <path
            d="M20 85 Q10 85 5 82"
            stroke="currentColor"
            strokeWidth="1.5"
            opacity="0.15"
            fill="none"
          />
        </svg>
      </div>

      {/* Second vessel — smaller, background */}
      <div
        className={`absolute top-[35%] transition-all duration-[2000ms] ease-in-out ${
          isLoggingIn
            ? 'right-[-20%] opacity-0'
            : 'right-[5%] opacity-10'
        }`}
      >
        <svg
          width="160"
          height="60"
          viewBox="0 0 280 100"
          fill="none"
          className="text-slate-500"
        >
          <path d="M20 70 L40 90 L240 90 L260 70 Z" fill="currentColor" opacity="0.3" />
          <rect x="50" y="50" width="180" height="20" rx="2" fill="currentColor" opacity="0.25" />
          <rect x="180" y="25" width="40" height="25" rx="2" fill="currentColor" opacity="0.3" />
          <rect x="60" y="35" width="25" height="15" rx="1" fill="#3b82f6" opacity="0.3" />
          <rect x="88" y="35" width="25" height="15" rx="1" fill="#f59e0b" opacity="0.3" />
          <rect x="116" y="35" width="25" height="15" rx="1" fill="#ef4444" opacity="0.3" />
        </svg>
      </div>

      {/* Login Card */}
      <div className="relative z-10 min-h-screen flex items-center justify-center p-4">
        <div
          className={`w-full max-w-md transition-all duration-700 ${
            isLoggingIn ? 'scale-95 opacity-80' : 'scale-100 opacity-100'
          }`}
        >
          <div className="bg-white/80 backdrop-blur-xl border border-white/60 shadow-2xl shadow-blue-900/5 rounded-2xl p-8">
            {/* Logo / Branding */}
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-14 h-14 bg-primary rounded-xl mb-4">
                <span className="material-symbols-outlined text-on-primary text-3xl">
                  sailing
                </span>
              </div>
              <h1 className="text-headline-md text-on-surface font-semibold">
                Logistics ERP
              </h1>
              <p className="text-body-md text-on-surface-variant mt-1">
                Enterprise Freight Management
              </p>
            </div>

            {/* Error message */}
            {serverError && (
              <div className="mb-5 flex items-center gap-2 px-4 py-3 bg-error-container/60 border border-error/20 rounded-xl">
                <span className="material-symbols-outlined text-error text-[18px]">error</span>
                <p className="text-body-md text-on-error-container">{serverError}</p>
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
              {/* Username */}
              <div>
                <label
                  htmlFor="username"
                  className="block text-label-lg text-on-surface font-medium mb-1.5"
                >
                  Username
                </label>
                <div className="relative">
                  <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">
                    person
                  </span>
                  <input
                    {...register('username')}
                    id="username"
                    type="text"
                    autoComplete="username"
                    autoFocus
                    placeholder="Enter your username"
                    className={`w-full pl-10 pr-4 py-3 rounded-xl border bg-white/60 text-body-lg text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all ${
                      errors.username ? 'border-error' : 'border-outline-variant'
                    }`}
                  />
                </div>
                {errors.username && (
                  <p className="mt-1 text-body-sm text-error">{errors.username.message}</p>
                )}
              </div>

              {/* Password */}
              <div>
                <label
                  htmlFor="password"
                  className="block text-label-lg text-on-surface font-medium mb-1.5"
                >
                  Password
                </label>
                <div className="relative">
                  <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">
                    lock
                  </span>
                  <input
                    {...register('password')}
                    id="password"
                    type="password"
                    autoComplete="current-password"
                    placeholder="Enter your password"
                    className={`w-full pl-10 pr-4 py-3 rounded-xl border bg-white/60 text-body-lg text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all ${
                      errors.password ? 'border-error' : 'border-outline-variant'
                    }`}
                  />
                </div>
                {errors.password && (
                  <p className="mt-1 text-body-sm text-error">{errors.password.message}</p>
                )}
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full mt-2 flex items-center justify-center gap-2 py-3.5 bg-primary text-on-primary rounded-xl font-semibold text-body-lg hover:bg-primary/90 disabled:opacity-60 disabled:cursor-not-allowed transition-all shadow-lg shadow-primary/20"
              >
                {isSubmitting ? (
                  <>
                    <div className="w-5 h-5 border-2 border-on-primary/30 border-t-on-primary rounded-full animate-spin" />
                    Signing in...
                  </>
                ) : (
                  <>
                    <span className="material-symbols-outlined text-[20px]">login</span>
                    Sign In
                  </>
                )}
              </button>
            </form>

            {/* Footer */}
            <p className="text-center text-body-sm text-on-surface-variant mt-6">
              Secure access to your freight operations
            </p>
          </div>
        </div>
      </div>

      {/* CSS Keyframes for floating animation */}
      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          50% { transform: translateY(-12px) rotate(1deg); }
        }
      `}</style>
    </div>
  );
}
