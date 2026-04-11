import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { X, ArrowRight, Sparkles, ShoppingBag, Info, ChevronLeft, ChevronRight, Tag, ArrowLeft } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { searchTiles } from "../lib/api";
import { cn } from "@/src/lib/utils";
import { Message, Tile } from "@/src/types";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface ChatModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function ChatModal({ isOpen, onClose }: ChatModalProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "model",
      text: "Welcome! I’ll help you choose tiles that fit your space perfectly—from style and size to finish and everything in between. Where would you like to start?",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [selectedTileIndex, setSelectedTileIndex] = useState<number | null>(null);
  const [selectedTilesList, setSelectedTilesList] = useState<Tile[]>([]);
  const [guidedIndex, setGuidedIndex] = useState<number | null>(0);
  const [guidedSelections, setGuidedSelections] = useState<Record<string, string>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const DISCOVERY_STEPS = [
    {
      id: "look",
      question: "Choose a look you like",
      options: ["Concrete", "Marble", "Stone", "Wood", "Metal", "Minimal"]
    },
    {
      id: "usage",
      question: "Floor or wall?",
      options: ["Floor", "Wall", "Both"]
    },
    {
      id: "space",
      question: "Where is this going?",
      options: ["Living Room", "Bedroom", "Bathroom", "Kitchen", "Outdoor", "Commercial Space"]
    },
    {
      id: "finish",
      question: "Finish preference?",
      options: ["Matt", "Polished", "Honed", "Not Sure"]
    },
    {
      id: "color",
      question: "Any color in mind?",
      options: ["Light", "Neutral", "Grey", "Dark", "Warm", "Cool", "No Preference"]
    }
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: userMessage }]);
    setIsLoading(true);

    try {
      // Collect last 10 messages as context history for deeper memory
      const history = messages.slice(-10).map(m => ({ role: m.role, text: m.text }));

      // Call our backend instead of calling Gemini directly on the client
      const response = await searchTiles(userMessage, history);

      // Merge AI's "why_recommended" into the full tile details from results
      const highlightedTiles = response.ai_response.recommended_tiles.map(rec => {
        const fullTile = response.results.find(t => t.sku === rec.sku);
        return { ...fullTile, ...rec } as Tile;
      }).filter(t => t.sku); // Ensure we have a valid tile

      setMessages((prev) => [
        ...prev,
        {
          role: "model",
          text: response.ai_response.ai_summary,
          tiles: highlightedTiles.length > 0 ? highlightedTiles : response.results.slice(0, 4)
        }
      ]);
    } catch (error) {
      console.error("Chat Error:", error);
      setMessages((prev) => [
        ...prev,
        { role: "model", text: "I apologize, but I'm having a bit of trouble connecting to our digital showroom right now. Please try again in a moment." },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleOpenDetails = (tiles: Tile[], index: number) => {
    setSelectedTilesList(tiles);
    setSelectedTileIndex(index);
  };

  const handleCloseDetails = () => {
    setSelectedTileIndex(null);
  };

  const handleNextTile = () => {
    if (selectedTileIndex !== null && selectedTileIndex < selectedTilesList.length - 1) {
      setSelectedTileIndex(selectedTileIndex + 1);
    }
  };

  const handlePrevTile = () => {
    if (selectedTileIndex !== null && selectedTileIndex > 0) {
      setSelectedTileIndex(selectedTileIndex - 1);
    }
  };

  // Helper to generate 'Best For' tags from suitability data
  const getBestForTags = (tile: Tile) => {
    const tags = new Set<string>();
    const source = (tile.suitable_for + " " + tile.application).toLowerCase();

    if (source.includes("bathroom") || source.includes("bath")) tags.add("Bathroom");
    if (source.includes("kitchen")) tags.add("Kitchen");
    if (source.includes("living") || source.includes("room")) tags.add("Living Area");
    if (source.includes("commercial") || source.includes("office")) tags.add("Commercial");
    if (source.includes("outdoor") || source.includes("exterior")) tags.add("Outdoor");
    if (source.includes("floor")) tags.add("Floor");
    if (source.includes("wall")) tags.add("Wall");
    if (tile.surface.toLowerCase().includes("matt")) tags.add("Matte");
    if (tile.surface.toLowerCase().includes("polished") || tile.surface.toLowerCase().includes("gloss")) tags.add("Polished");

    return Array.from(tags);
  };

  const handleGuidedOption = async (option: string) => {
    if (guidedIndex === null) return;

    const step = DISCOVERY_STEPS[guidedIndex];
    const newSelections = { ...guidedSelections, [step.id]: option };
    setGuidedSelections(newSelections);

    if (guidedIndex < DISCOVERY_STEPS.length - 1) {
      setGuidedIndex(guidedIndex + 1);
    } else {
      // Final step reached, construct and send query
      setGuidedIndex(null);
      const queryParts = [
        newSelections.look ? `${newSelections.look} look` : "",
        newSelections.usage !== "Both" ? `${newSelections.usage} tiles` : "tiles",
        newSelections.space ? `for ${newSelections.space}` : "",
        newSelections.finish && newSelections.finish !== "Not Sure" ? `in ${newSelections.finish} finish` : "",
        newSelections.color && newSelections.color !== "No Preference" ? `and ${newSelections.color} color` : ""
      ].filter(Boolean);

      const combinedQuery = queryParts.join(" ");
      setMessages(prev => [...prev, { role: "user", text: combinedQuery }]);

      setIsLoading(true);
      try {
        // Use functional update or capture the current messages to avoid stale state
        const history = [...messages.slice(-9).map(m => ({ role: m.role, text: m.text })), { role: "user" as const, text: combinedQuery }];
        const response = await searchTiles(combinedQuery, history);

        const highlightedTiles = (response.ai_response?.recommended_tiles || []).map(rec => {
          const fullTile = response.results.find(t => t.sku === rec.sku);
          return fullTile ? { ...fullTile, ...rec } : null;
        }).filter(Boolean) as Tile[];

        setMessages((prev) => [
          ...prev,
          {
            role: "model",
            text: response.ai_response.ai_summary,
            tiles: highlightedTiles.length > 0 ? highlightedTiles : response.results.slice(0, 4)
          }
        ]);
      } catch (err) {
        console.error("Guided Submission Error:", err);
        setMessages((prev) => [...prev, { role: "model", text: "I apologize, but I encountered a slight issue while processing your selection. Could you please try typing your request instead? I'm here to help." }]);
      } finally {
        setIsLoading(false);
      }
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 md:p-8">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-charcoal/60 backdrop-blur-md"
            onClick={onClose}
          />

          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="relative w-full max-w-6xl h-[85vh] flex flex-col shadow-2xl overflow-hidden glass-morphism-dark border border-gold/20"
          >
            {/* Header */}
            <div className="h-16 w-full flex items-center justify-between px-8 bg-charcoal border-b border-gold/10">
              <div className="flex items-center gap-5">
                <div className="flex gap-2">
                  <div className="w-3 h-3 rounded-full bg-gold/40" />
                  <div className="w-3 h-3 rounded-full bg-gold/40" />
                  <div className="w-3 h-3 rounded-full bg-gold/40" />
                </div>
                <span className="font-jost text-[11px] tracking-[0.4em] uppercase text-gold font-bold ml-4">
                  Tile Advisor
                </span>
              </div>
              <button
                onClick={onClose}
                className="text-gold/60 hover:text-gold transition-colors"
              >
                <X size={24} />
              </button>
            </div>

            <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
              {/* Main Chat Area */}
              <div className="flex-1 flex flex-col overflow-hidden bg-charcoal/30">
                <div className="flex-1 overflow-y-auto p-6 md:p-14 space-y-10 scrollbar-thin scrollbar-thumb-gold/20">
                  {messages.map((msg, idx) => (
                    <div key={idx} className={cn("flex gap-6 md:gap-8 max-w-4xl", msg.role === "user" && "flex-row-reverse text-right ml-auto")}>
                      <div className={cn(
                        "w-12 h-12 shrink-0 flex items-center justify-center font-headline text-2xl border border-gold/20",
                        msg.role === "model" ? "bg-charcoal text-gold" : "bg-gold text-charcoal"
                      )}>
                        {msg.role === "model" ? "🤖" : "👤"}
                      </div>
                      <div className="space-y-3">
                        <div className="font-body text-base md:text-lg text-white/90 leading-relaxed font-light prose prose-invert prose-gold max-w-none">
                          <ReactMarkdown>{msg.text}</ReactMarkdown>
                        </div>

                        {/* Tile Recommendations */}
                        {msg.tiles && msg.tiles.length > 0 && (
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-6">
                            {msg.tiles.map((tile, tidx) => (
                              <div key={tidx} className="group relative bg-white/5 border border-gold/10 hover:border-gold/30 transition-all p-4 flex flex-col gap-4">
                                {tile.image_path && (
                                  <div className="aspect-[4/3] overflow-hidden bg-charcoal">
                                    <img
                                      src={`${API_BASE_URL}/images/${tile.image_path}`}
                                      alt={tile.series_name}
                                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                                      onError={(e) => {
                                        (e.target as HTMLImageElement).src = "/images/tile-placeholder.png";
                                      }}
                                    />
                                  </div>
                                )}
                                <div>
                                  <div className="flex justify-between items-start mb-1">
                                    <h5 className="text-gold font-jost text-xs tracking-widest uppercase font-bold">{tile.series_name}</h5>
                                    <span className="text-[10px] text-gold/40 font-mono">{tile.sku}</span>
                                  </div>
                                  <p className="text-[11px] text-white/60 font-jost uppercase tracking-wider">
                                    {tile.color} • {tile.surface} • {tile.size_cm}
                                  </p>
                                </div>

                                {tile.why_recommended && (
                                  <div className="bg-gold/5 border-l-2 border-gold p-3">
                                    <p className="text-[10px] text-gold/80 italic font-body leading-relaxed">
                                      "{tile.why_recommended}"
                                    </p>
                                  </div>
                                )}

                                <div className="flex gap-2 pt-2 border-t border-gold/5">
                                  <button
                                    onClick={() => handleOpenDetails(msg.tiles!, tidx)}
                                    className="flex-1 py-2 text-[10px] font-jost font-bold uppercase tracking-widest border border-gold/20 hover:bg-gold/10 text-gold transition-colors flex items-center justify-center gap-2"
                                  >
                                    <Info size={12} /> Details
                                  </button>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}

                        {msg.role === "model" && idx === 0 && guidedIndex !== null && !input.trim() && (
                          <div className="mt-8 space-y-6">
                            <div className="flex items-center gap-3">
                              <div className="h-px flex-1 bg-gold/10" />
                              <span className="text-[10px] font-jost font-bold uppercase tracking-[0.3em] text-gold/60">
                                Guided Discovery Step {guidedIndex + 1}/5
                              </span>
                              <div className="h-px flex-1 bg-gold/10" />
                            </div>

                            <div className="space-y-4">
                              <h4 className="text-sm font-headline text-white tracking-wide uppercase">
                                {DISCOVERY_STEPS[guidedIndex].question}
                              </h4>
                              <div className="flex flex-wrap gap-2">
                                {DISCOVERY_STEPS[guidedIndex].options.map((opt) => (
                                  <button
                                    key={opt}
                                    onClick={() => handleGuidedOption(opt)}
                                    className="px-5 py-2.5 border border-gold/20 hover:border-gold/60 text-[10px] font-jost uppercase font-bold tracking-widest text-gold hover:bg-gold/10 transition-all bg-white/5"
                                  >
                                    {opt}
                                  </button>
                                ))}
                              </div>
                            </div>

                            <div className="flex items-center gap-6">
                              {guidedIndex > 0 && (
                                <button
                                  onClick={() => setGuidedIndex(guidedIndex - 1)}
                                  className="text-[9px] font-jost uppercase tracking-widest text-white/30 hover:text-gold transition-colors underline underline-offset-4 decoration-white/10"
                                >
                                  ← Go Back
                                </button>
                              )}
                              <button
                                onClick={() => {
                                  setGuidedIndex(0);
                                  setGuidedSelections({});
                                }}
                                className="text-[9px] font-jost uppercase tracking-widest text-white/30 hover:text-gold transition-colors underline underline-offset-4 decoration-white/10"
                              >
                                Clear Selection & Start Over
                              </button>
                            </div>
                          </div>
                        )}
                        <span className="block text-[10px] tracking-[0.3em] text-gold font-bold uppercase opacity-60">
                          {msg.role === "model" ? "Advisor" : "Client"}
                        </span>
                      </div>
                    </div>
                  ))}
                  {isLoading && (
                    <div className="flex gap-8 max-w-4xl animate-pulse">
                      <div className="w-12 h-12 bg-charcoal shrink-0 flex items-center justify-center font-headline text-gold text-2xl border border-gold/20">🤖</div>
                      <div className="space-y-2">
                        <div className="h-4 w-48 bg-gold/20" />
                        <div className="h-4 w-32 bg-gold/20" />
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>

                {/* Input Area */}
                <div className="p-6 md:p-10 md:px-14 border-t border-gold/10">
                  <form
                    onSubmit={(e) => { e.preventDefault(); handleSend(); }}
                    className="relative flex items-center"
                  >
                    <input
                      className="w-full bg-transparent border-0 border-b-2 border-gold py-6 text-sm font-jost tracking-[0.2em] uppercase focus:ring-0 focus:border-gold font-medium text-white placeholder:text-white/30 outline-none"
                      placeholder="Type your inquiry here..."
                      type="text"
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      disabled={isLoading}
                    />
                    <button
                      type="submit"
                      disabled={isLoading}
                      className="absolute right-0 hover:text-gold transition-all text-gold disabled:opacity-50"
                    >
                      <ArrowRight size={32} />
                    </button>
                  </form>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Product Details Overlay */}
          <AnimatePresence>
            {selectedTileIndex !== null && (
              <>
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="absolute inset-0 z-[110] bg-black/40 backdrop-blur-sm"
                  onClick={handleCloseDetails}
                />
                <motion.div
                  initial={{ x: "100%" }}
                  animate={{ x: 0 }}
                  exit={{ x: "100%" }}
                  transition={{ type: "spring", damping: 30, stiffness: 300 }}
                  className="absolute right-0 top-0 bottom-0 z-[120] w-full md:w-[500px] bg-charcoal shadow-2xl border-l border-gold/20 flex flex-col"
                >
                  {/* Details Header */}
                  <div className="h-20 shrink-0 flex items-center justify-between px-8 border-b border-gold/10 bg-black/20">
                    <button
                      onClick={handleCloseDetails}
                      className="flex items-center gap-3 text-gold/60 hover:text-gold transition-colors font-jost text-[10px] uppercase font-bold tracking-widest"
                    >
                      <ArrowLeft size={18} /> Back to Chat
                    </button>
                    <div className="flex items-center gap-4">
                      <span className="font-mono text-[10px] text-gold/40">
                        {selectedTileIndex + 1} / {selectedTilesList.length}
                      </span>
                    </div>
                  </div>

                  {/* Details Content */}
                  <div className="flex-1 overflow-y-auto p-8 md:p-10 space-y-10 scrollbar-thin scrollbar-thumb-gold/20">
                    {/* Hero Image */}
                    <div className="relative group aspect-square bg-black/40 border border-gold/10 overflow-hidden">
                      <img
                        src={`${API_BASE_URL}/images/${selectedTilesList[selectedTileIndex].image_path}`}
                        alt={selectedTilesList[selectedTileIndex].series_name}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          e.currentTarget.src = "/images/tile-placeholder.png";
                        }}
                      />

                      {/* Nav Arrows */}
                      <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 flex justify-between px-4 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={(e) => { e.stopPropagation(); handlePrevTile(); }}
                          disabled={selectedTileIndex === 0}
                          className="w-10 h-10 rounded-full bg-black/60 border border-gold/20 flex items-center justify-center text-gold disabled:opacity-20 hover:bg-gold/20 transition-all"
                        >
                          <ChevronLeft size={20} />
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleNextTile(); }}
                          disabled={selectedTileIndex === selectedTilesList.length - 1}
                          className="w-10 h-10 rounded-full bg-black/60 border border-gold/20 flex items-center justify-center text-gold disabled:opacity-20 hover:bg-gold/20 transition-all"
                        >
                          <ChevronRight size={20} />
                        </button>
                      </div>
                    </div>

                    {/* Basic Info */}
                    <div className="space-y-4">
                      <div className="flex justify-between items-end">
                        <h2 className="text-3xl font-headline text-white tracking-wide">
                          {selectedTilesList[selectedTileIndex].series_name}
                        </h2>
                        <span className="text-[10px] font-mono text-gold/60 bg-gold/5 px-2 py-1 border border-gold/10 lowercase">
                          SKU: {selectedTilesList[selectedTileIndex].sku}
                        </span>
                      </div>

                      {/* Tags */}
                      <div className="flex flex-wrap gap-2">
                        {getBestForTags(selectedTilesList[selectedTileIndex]).map(tag => (
                          <span key={tag} className="flex items-center gap-1.5 px-3 py-1 bg-gold/5 border border-gold/10 text-[9px] font-jost uppercase font-bold tracking-wider text-gold/80 hover:bg-gold/10 transition-colors">
                            <Tag size={10} /> {tag}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Technical Specs Grid */}
                    <div className="pt-6 border-t border-gold/10">
                      <h4 className="text-[10px] font-jost font-bold uppercase tracking-[0.3em] text-gold/60 mb-6 underline underline-offset-8 decoration-gold/20">Technical Specifications</h4>
                      <div className="grid grid-cols-2 gap-y-8 gap-x-12">
                        {[
                          { label: "Collection", value: selectedTilesList[selectedTileIndex].series_name },
                          { label: "Color", value: selectedTilesList[selectedTileIndex].color },
                          { label: "Surface Finish", value: selectedTilesList[selectedTileIndex].surface },
                          { label: "Dimensions", value: selectedTilesList[selectedTileIndex].size_cm },
                          { label: "Application", value: selectedTilesList[selectedTileIndex].application },
                        ].map((spec) => (
                          <div key={spec.label} className="space-y-1.5">
                            <p className="text-[9px] font-jost uppercase tracking-[0.2em] text-gold/40">{spec.label}</p>
                            <p className="text-xs font-semibold text-white/90 tracking-wide uppercase">{spec.value}</p>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* AI Wisdom */}
                    {selectedTilesList[selectedTileIndex].why_recommended && (
                      <div className="p-8 bg-charcoal-light/50 border border-gold/10 relative overflow-hidden group">
                        <div className="absolute top-0 left-0 w-1 h-full bg-gold/40" />
                        <Sparkles className="absolute top-4 right-4 text-gold/10 w-12 h-12" />
                        <h4 className="text-[10px] font-jost font-bold uppercase tracking-[0.3em] text-gold/60 mb-4 flex items-center gap-2">
                          <Sparkles size={12} className="text-gold" /> Why Recommended
                        </h4>
                        <p className="text-sm font-body text-white/80 leading-relaxed italic relative z-10">
                          "{selectedTilesList[selectedTileIndex].why_recommended}"
                        </p>
                      </div>
                    )}

                    {/* Action */}
                    <button className="w-full py-5 bg-gold text-charcoal font-jost font-bold uppercase tracking-[0.4em] text-[11px] hover:bg-white transition-all flex items-center justify-center gap-3 group">
                      <ShoppingBag size={16} className="group-hover:scale-110 transition-transform" /> Request Architectural Quote
                    </button>
                  </div>
                </motion.div>
              </>
            )}
          </AnimatePresence>
        </div>
      )}
    </AnimatePresence>
  );
}
