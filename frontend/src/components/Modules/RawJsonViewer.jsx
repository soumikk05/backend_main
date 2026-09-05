import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Code2, ChevronDown, ChevronUp, Copy, Check } from 'lucide-react';

export function RawJsonViewer({ data, title = "Raw API Response" }) {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  if (!data) return null;

  const jsonString = JSON.stringify(data, null, 2);

  const handleCopy = (e) => {
    e.stopPropagation();
    navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mt-6 rounded-xl border border-white/10 bg-black/40 backdrop-blur-md overflow-hidden transition-all duration-300">
      <div 
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between px-4 py-3 cursor-pointer select-none hover:bg-white/[0.03] transition-colors border-b border-transparent data-[open=true]:border-white/10"
        data-open={isOpen}
      >
        <div className="flex items-center gap-2.5">
          <Code2 size={16} className="text-cyan-400" />
          <span className="font-mono text-xs uppercase tracking-wider text-slate-300">
            {title}
          </span>
          <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-slate-400 border border-white/5">
            JSON
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono rounded-md bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10 transition-colors"
            title="Copy JSON to clipboard"
          >
            {copied ? (
              <>
                <Check size={12} className="text-emerald-400" />
                <span className="text-emerald-400">Copied</span>
              </>
            ) : (
              <>
                <Copy size={12} className="text-slate-400" />
                <span>Copy</span>
              </>
            )}
          </button>
          <div className="text-slate-400">
            {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </div>
        </div>
      </div>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div className="p-4 max-h-96 overflow-y-auto font-mono text-xs text-cyan-200/90 bg-[#030712]/80 leading-relaxed scrollbar-thin">
              <pre className="whitespace-pre-wrap break-all">{jsonString}</pre>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
