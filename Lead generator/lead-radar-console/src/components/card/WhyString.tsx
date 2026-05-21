export function WhyString({ text }: { text: string }) {
  return (
    <div className="text-xs text-zinc-400 px-4 py-1 border-b border-zinc-900">
      <span className="mr-2">ⓘ</span>Why: {text}
    </div>
  );
}
