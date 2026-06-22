import { useState, useRef, useEffect } from 'react';
import { useAuth } from '@/auth/useAuth';
import { useProfile, useUpdateProfile, useUploadAvatar } from './useProfile';
import type { ProfileUpdatePayload } from './useProfile';

export default function ProfilePage() {
  const { refreshUser } = useAuth();
  const { data: profile, isLoading } = useProfile();
  const updateProfile = useUpdateProfile();
  const uploadAvatar = useUploadAvatar();

  const fileInputRef = useRef<HTMLInputElement>(null);

  const [form, setForm] = useState<ProfileUpdatePayload>({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    department: '',
  });
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Populate form once profile loads
  useEffect(() => {
    if (profile) {
      setForm({
        first_name: profile.first_name ?? '',
        last_name: profile.last_name ?? '',
        email: profile.email ?? '',
        phone: profile.phone ?? '',
        department: profile.department ?? '',
      });
    }
  }, [profile]);

  // Auto-dismiss toast
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  const handleChange = (field: keyof ProfileUpdatePayload, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await updateProfile.mutateAsync(form);
      await refreshUser();
      setToast({ type: 'success', message: 'Profile updated successfully.' });
    } catch {
      setToast({ type: 'error', message: 'Failed to update profile. Please try again.' });
    }
  };

  const handleAvatarClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 2 * 1024 * 1024) {
      setToast({ type: 'error', message: 'File size must be under 2 MB.' });
      return;
    }

    if (!file.type.startsWith('image/')) {
      setToast({ type: 'error', message: 'Only image files are allowed.' });
      return;
    }

    try {
      await uploadAvatar.mutateAsync(file);
      await refreshUser();
      setToast({ type: 'success', message: 'Avatar updated successfully.' });
    } catch {
      setToast({ type: 'error', message: 'Failed to upload avatar. Please try again.' });
    }

    // Reset file input so the same file can be re-uploaded
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 border-3 border-primary/30 border-t-primary rounded-full animate-spin" />
      </div>
    );
  }

  const initials = profile
    ? `${profile.first_name.charAt(0)}${profile.last_name.charAt(0)}`.toUpperCase()
    : '';

  return (
    <div className="max-w-2xl mx-auto">
      {/* Toast notification */}
      {toast && (
        <div
          className={`fixed top-20 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded-xl shadow-lg text-body-md font-medium transition-all ${
            toast.type === 'success'
              ? 'bg-primary-container text-on-primary-container'
              : 'bg-error-container text-on-error-container'
          }`}
        >
          <span className="material-symbols-outlined text-[20px]">
            {toast.type === 'success' ? 'check_circle' : 'error'}
          </span>
          {toast.message}
        </div>
      )}

      <h1 className="text-headline-md text-on-surface font-semibold mb-6">My Profile</h1>

      <div className="bg-surface rounded-2xl border border-outline-variant shadow-sm overflow-hidden">
        {/* Avatar section */}
        <div className="flex flex-col items-center py-8 border-b border-outline-variant bg-surface-variant/30">
          <button
            type="button"
            onClick={handleAvatarClick}
            className="relative group w-24 h-24 rounded-full overflow-hidden focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
            aria-label="Change profile picture"
          >
            {profile?.avatar_url ? (
              <img
                src={profile.avatar_url}
                alt="Profile avatar"
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full bg-primary-container text-on-primary-container flex items-center justify-center text-headline-md font-semibold">
                {initials}
              </div>
            )}
            {/* Hover overlay */}
            <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
              <span className="material-symbols-outlined text-white text-[28px]">
                photo_camera
              </span>
            </div>
          </button>

          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={handleFileChange}
            aria-label="Upload avatar file"
          />

          <button
            type="button"
            onClick={handleAvatarClick}
            className="mt-3 text-body-md text-primary font-medium hover:underline"
          >
            Change photo
          </button>

          {uploadAvatar.isPending && (
            <p className="mt-2 text-body-sm text-on-surface-variant">Uploading...</p>
          )}
        </div>

        {/* Profile form */}
        <form onSubmit={handleSave} className="p-6 space-y-5">
          {/* Username (read-only) */}
          <div>
            <label className="block text-body-sm text-on-surface-variant font-medium mb-1">
              Username
            </label>
            <div className="flex items-center gap-2 px-3 py-2.5 bg-surface-variant rounded-xl text-body-md text-on-surface">
              <span className="material-symbols-outlined text-[18px] text-on-surface-variant">
                person
              </span>
              {profile?.username}
            </div>
          </div>

          {/* Role (read-only badge) */}
          <div>
            <label className="block text-body-sm text-on-surface-variant font-medium mb-1">
              Role
            </label>
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-secondary-container text-on-secondary-container rounded-full text-label-lg font-medium">
              <span className="material-symbols-outlined text-[16px]">badge</span>
              {profile?.role}
            </span>
          </div>

          {/* Name fields */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="first_name" className="block text-body-sm text-on-surface-variant font-medium mb-1">
                First Name
              </label>
              <div className="relative">
                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-[18px] text-on-surface-variant">
                  id_card
                </span>
                <input
                  id="first_name"
                  type="text"
                  value={form.first_name}
                  onChange={(e) => handleChange('first_name', e.target.value)}
                  className="w-full pl-10 pr-3 py-2.5 rounded-xl border border-outline-variant bg-surface text-body-md text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-colors"
                />
              </div>
            </div>
            <div>
              <label htmlFor="last_name" className="block text-body-sm text-on-surface-variant font-medium mb-1">
                Last Name
              </label>
              <div className="relative">
                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-[18px] text-on-surface-variant">
                  id_card
                </span>
                <input
                  id="last_name"
                  type="text"
                  value={form.last_name}
                  onChange={(e) => handleChange('last_name', e.target.value)}
                  className="w-full pl-10 pr-3 py-2.5 rounded-xl border border-outline-variant bg-surface text-body-md text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-colors"
                />
              </div>
            </div>
          </div>

          {/* Email */}
          <div>
            <label htmlFor="email" className="block text-body-sm text-on-surface-variant font-medium mb-1">
              Email
            </label>
            <div className="relative">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-[18px] text-on-surface-variant">
                mail
              </span>
              <input
                id="email"
                type="email"
                value={form.email}
                onChange={(e) => handleChange('email', e.target.value)}
                className="w-full pl-10 pr-3 py-2.5 rounded-xl border border-outline-variant bg-surface text-body-md text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-colors"
              />
            </div>
          </div>

          {/* Phone */}
          <div>
            <label htmlFor="phone" className="block text-body-sm text-on-surface-variant font-medium mb-1">
              Phone
            </label>
            <div className="relative">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-[18px] text-on-surface-variant">
                call
              </span>
              <input
                id="phone"
                type="tel"
                value={form.phone}
                onChange={(e) => handleChange('phone', e.target.value)}
                className="w-full pl-10 pr-3 py-2.5 rounded-xl border border-outline-variant bg-surface text-body-md text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-colors"
              />
            </div>
          </div>

          {/* Department */}
          <div>
            <label htmlFor="department" className="block text-body-sm text-on-surface-variant font-medium mb-1">
              Department
            </label>
            <div className="relative">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-[18px] text-on-surface-variant">
                corporate_fare
              </span>
              <input
                id="department"
                type="text"
                value={form.department}
                onChange={(e) => handleChange('department', e.target.value)}
                className="w-full pl-10 pr-3 py-2.5 rounded-xl border border-outline-variant bg-surface text-body-md text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-colors"
              />
            </div>
          </div>

          {/* Save button */}
          <div className="pt-2">
            <button
              type="submit"
              disabled={updateProfile.isPending}
              className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-2.5 bg-primary text-on-primary rounded-xl font-medium text-body-md hover:bg-primary/90 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
            >
              {updateProfile.isPending ? (
                <>
                  <div className="w-4 h-4 border-2 border-on-primary/30 border-t-on-primary rounded-full animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-[18px]">save</span>
                  Save Changes
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
