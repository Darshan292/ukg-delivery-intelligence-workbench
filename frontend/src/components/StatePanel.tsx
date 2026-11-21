// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

type Props =
  | { kind: "loading"; entity: string }
  | { kind: "empty"; entity: string }
  | { kind: "error"; entity: string; message: string };

export function StatePanel(props: Props) {
  const box = "border border-line rounded-[2px] bg-surface p-4 max-w-[70ch]";
  if (props.kind === "loading")
    return (
      <p role="status" className={box}>
        Loading links for <span className="font-mono">{props.entity}</span>
      </p>
    );
  if (props.kind === "error")
    return (
      <p role="alert" className={box}>
        {props.message}
      </p>
    );
  return (
    <p className={box}>
      <span className="font-mono">{props.entity}</span>
      {" has no stored links yet."}
    </p>
  );
}
