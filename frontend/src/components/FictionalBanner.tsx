// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

const DEFAULT_TEXT =
  "FICTIONAL synthetic data. Not UKG behaviour. Independent community project, not affiliated with UKG Inc.";

export function FictionalBanner({ text = DEFAULT_TEXT }: { text?: string }) {
  return (
    <div
      role="note"
      className="border-b border-banner-line bg-banner-bg px-4 py-2 text-[13px] font-medium text-banner-ink"
    >
      {text}
    </div>
  );
}
