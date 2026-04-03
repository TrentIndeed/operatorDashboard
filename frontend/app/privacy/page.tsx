export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-[#E4E4E7] p-8 max-w-3xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Privacy Policy</h1>
      <p className="text-sm text-[#9494AD] mb-8">Last updated: April 3, 2026</p>

      <div className="space-y-6 text-sm leading-relaxed text-[#9494AD]">
        <section>
          <h2 className="text-lg font-semibold text-white mb-2">What We Collect</h2>
          <p>When you create an account, we collect your username and password (hashed). If you opt into SMS or Telegram notifications, we store your phone number or Telegram chat ID. We also store your projects, goals, and tasks that you enter into the dashboard.</p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-white mb-2">How We Use Your Data</h2>
          <p>Your data is used solely to power your personal dashboard. AI-generated tasks, content drafts, and suggestions are based on the projects and goals you provide. Notification messages (SMS/Telegram) are sent only to you at the phone number or chat ID you configure.</p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-white mb-2">Third-Party Services</h2>
          <p>We use the following third-party services to operate the dashboard:</p>
          <ul className="list-disc pl-6 mt-2 space-y-1">
            <li>Claude AI (Anthropic) — for generating tasks, content, and suggestions</li>
            <li>Twilio — for optional SMS notifications (only to your configured number)</li>
            <li>Telegram Bot API — for optional Telegram notifications</li>
            <li>GitHub API — for syncing your repository data</li>
            <li>Google/YouTube API — for syncing video analytics</li>
            <li>Stripe — for payment processing (cloud plans only)</li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-white mb-2">Data Sharing</h2>
          <p>We do not sell, share, or distribute your personal information to any third parties for marketing purposes. Your data is only shared with the third-party services listed above as necessary to provide the dashboard functionality.</p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-white mb-2">Data Storage</h2>
          <p>Your data is stored in a SQLite database on your self-hosted server (local plan) or on a dedicated VPS (cloud plans). You can delete all your data at any time from the Settings page.</p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-white mb-2">SMS/Notifications</h2>
          <p>If you configure SMS notifications, messages are sent only to the phone number you provide. You can opt out at any time by replying STOP, removing your phone number from settings, or disabling notifications. Message frequency is up to 4 messages per day. Standard message and data rates may apply.</p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-white mb-2">Contact</h2>
          <p>For questions about this privacy policy, contact us through the dashboard or at the support channels listed on the landing page.</p>
        </section>
      </div>
    </div>
  );
}
