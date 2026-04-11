import { motion } from "motion/react";
import { Grid, Leaf, Archive, Sparkles, X } from "lucide-react";
import { cn } from "@/src/lib/utils";

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function Sidebar({ isOpen, onClose }: SidebarProps) {
  const navItems = [
    { label: "ADVISORY", icon: Sparkles, active: true },
    { label: "CATALOG", icon: Grid },
    { label: "SUSTAINABILITY", icon: Leaf },
    { label: "ARCHIVE", icon: Archive },
  ];

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div 
          className="fixed inset-0 z-[55] bg-black/40 backdrop-blur-sm"
          onClick={onClose}
        />
      )}
      
      <motion.aside
        initial={{ x: "100%" }}
        animate={{ x: isOpen ? 0 : "100%" }}
        transition={{ type: "spring", damping: 30, stiffness: 200 }}
        className="fixed right-0 top-0 h-full z-[60] w-full max-w-[380px] flex flex-col p-10 bg-charcoal/95 backdrop-blur-3xl border-l border-gold/10 shadow-2xl"
      >
        <button 
          onClick={onClose}
          className="absolute top-6 right-6 text-gold/60 hover:text-gold transition-colors"
        >
          <X size={24} />
        </button>

        <div className="flex items-center gap-5 mb-16">
          <div className="w-14 h-14 bg-gold flex items-center justify-center shrink-0">
            <span className="text-charcoal font-headline text-2xl font-bold">C</span>
          </div>
          <div>
            <div className="text-gold font-bold text-xl font-jost tracking-[0.2em] uppercase leading-tight">
              THE CURATOR
            </div>
            <div className="text-white/40 font-jost font-light text-[11px] tracking-widest uppercase">
              Premium Sourcing
            </div>
          </div>
        </div>

        <nav className="flex flex-col gap-3">
          {navItems.map((item) => (
            <a
              key={item.label}
              href="#"
              className={cn(
                "flex items-center gap-5 p-5 font-jost font-light tracking-[0.2em] transition-all group",
                item.active 
                  ? "text-gold bg-gold/5 border-l-2 border-gold" 
                  : "text-white/70 hover:text-gold hover:bg-gold/5"
              )}
            >
              <item.icon className={cn("w-5 h-5", item.active ? "text-gold" : "text-white/40 group-hover:text-gold")} />
              {item.label}
            </a>
          ))}
        </nav>
      </motion.aside>
    </>
  );
}
