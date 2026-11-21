// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

const DEFAULT_TEXT =
  "FICTIONAL synthetic data. Not UKG behaviour. Independent community project, not affiliated with UKG Inc.";

export function FictionalBanner({ text = DEFAULT_TEXT }: { text?: string }) {
  return (
    <div
      role="note"
      className="border-b border-amber-700 bg-amber-100 px-4 py-2 text-sm font-medium text-amber-950"
    >
      {text}
    </div>
  );
}
