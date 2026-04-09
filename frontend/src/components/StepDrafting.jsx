import { useState } from 'react';

import { Loader2, Sparkles, Settings2, AlignLeft, Type, Video, Link as LinkIcon } from 'lucide-react';
import clsx from 'clsx';

export default function StepDrafting({ onDraftComplete }) {
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState('topic'); // 'topic' | 'text' | 'url'
  const [content, setContent] = useState('');
  
  // Settings with defaults
  const [settings, setSettings] = useState({
    niche: 'Tech',
    llmProviders: 'Groq',
    imageProvider: 'Gemini',
    ttsProvider: 'Sarvam'
  });

  const updateSetting = (key, val) => setSettings(s => ({ ...s, [key]: val }));

  const handleGenerate = async () => {
    if (!content.trim()) return;
    setLoading(true);

    try {
      // Prototype fetch matching the contract
      const response = await fetch('http://localhost:8000/api/draft', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          input_mode: mode === 'text' ? 'direct_text' : mode,
          content: content,
          niche: settings.niche.toLowerCase(),
          llm_provider: settings.llmProviders.toLowerCase(),
          image_provider: settings.imageProvider.toLowerCase(),
          tts_provider: settings.ttsProvider.toLowerCase()
        })
      });

      if (!response.ok) {
        throw new Error('Drafting failed');
      }

      const resJson = await response.json();
      if (resJson.status === 'success') {
        onDraftComplete({
          draft: resJson.data, 
          settings 
        });
      }
    } catch (err) {
      console.error(err);
      // Fallback for prototype testing if backend is dead
      alert("Error reaching backend. Is localhost:8000 running?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto w-full space-y-8">
      {/* Header */}
      <div className="text-center space-y-2">
        <div className="inline-flex items-center justify-center p-3 bg-primary/10 rounded-2xl mb-4">
          <Video className="w-8 h-8 text-primary" />
        </div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">The Drafting Studio</h1>
        <p className="text-muted-foreground">Configure your pipeline and ignite the creative process.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 bg-card border border-border p-6 rounded-2xl shadow-xl shadow-black/50">
        
        {/* Settings Panel */}
        <div className="md:col-span-4 space-y-6">
          <div className="flex items-center gap-2 text-foreground font-semibold pb-2 border-b border-border/50">
            <Settings2 className="w-4 h-4 text-primary" />
            <span>Configuration</span>
          </div>

          <div className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Niche</label>
              <select className="w-full" value={settings.niche} onChange={e => updateSetting('niche', e.target.value)}>
                <option value="General">General</option>
                <option value="Tech">Tech</option>
                <option value="Finance">Finance</option>
              </select>
            </div>
            
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">LLM Provider</label>
              <select className="w-full" value={settings.llmProviders} onChange={e => updateSetting('llmProviders', e.target.value)}>
                <option value="Ollama">Ollama (Local)</option>
                <option value="Groq">Groq</option>
                <option value="Claude">Claude</option>
                <option value="OpenAI">OpenAI</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Image Generator</label>
              <select className="w-full" value={settings.imageProvider} onChange={e => updateSetting('imageProvider', e.target.value)}>
                <option value="Gemini">Gemini</option>
                <option value="Pexels">Pexels (Stock)</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">TTS Provider</label>
              <select className="w-full" value={settings.ttsProvider} onChange={e => updateSetting('ttsProvider', e.target.value)}>
                <option value="Sarvam">Sarvam AI</option>
                <option value="Edge">Edge TTS</option>
                <option value="ElevenLabs">ElevenLabs</option>
              </select>
            </div>
          </div>
        </div>

        {/* Input Panel */}
        <div className="md:col-span-8 flex flex-col pt-6 md:pt-0 md:pl-6 md:border-l md:border-border/50 space-y-4">
          
          <div className="flex bg-secondary/30 p-1 rounded-lg border border-border shrink-0 self-start">
            <button 
              onClick={() => setMode('topic')}
              className={clsx(
                "px-4 py-1.5 text-sm font-medium rounded-md transition-colors flex items-center gap-2",
                mode === 'topic' ? "bg-background shadow text-foreground" : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
              )}
            >
              <Type className="w-4 h-4" />
              Topic
            </button>
            <button 
              onClick={() => setMode('text')}
              className={clsx(
                "px-4 py-1.5 text-sm font-medium rounded-md transition-colors flex items-center gap-2",
                mode === 'text' ? "bg-background shadow text-foreground" : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
              )}
            >
              <AlignLeft className="w-4 h-4" />
              Direct Text
            </button>
            <button 
              onClick={() => setMode('url')}
              className={clsx(
                "px-4 py-1.5 text-sm font-medium rounded-md transition-colors flex items-center gap-2",
                mode === 'url' ? "bg-background shadow text-foreground" : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
              )}
            >
              <LinkIcon className="w-4 h-4" />
              URL
            </button>
          </div>

          <div className="flex-1 min-h-[200px] flex flex-col relative group">
              {mode === 'topic' ? (
                <div className="flex-1 flex flex-col">
                  <input 
                    type="text" 
                    placeholder="E.g., How to build a custom PC in 2026..."
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    className="w-full flex-1 bg-secondary/10 border-border text-lg p-4 font-medium transition-all group-focus-within:bg-secondary/30"
                  />
                </div>
              ) : mode === 'url' ? (
                <div className="flex-1 flex flex-col">
                  <input 
                    type="url" 
                    placeholder="https://www.indiatoday.in/..."
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    className="w-full flex-1 bg-secondary/10 border-border text-lg p-4 font-medium transition-all group-focus-within:bg-secondary/30"
                  />
                </div>
              ) : (
                <div className="flex-1 flex flex-col">
                  <textarea 
                    placeholder="Paste raw information, article snippets, or unstructured thoughts..."
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    className="w-full flex-1 bg-secondary/10 border-border p-4 resize-none min-h-[200px] transition-all group-focus-within:bg-secondary/30"
                  />
                </div>
              )}
          </div>

          <button 
            onClick={handleGenerate}
            disabled={loading || !content.trim()}
            className="w-full py-3.5 bg-primary hover:bg-primaryHover text-primary-foreground rounded-lg font-semibold flex items-center justify-center gap-2 disabled:opacity-50 shadow-lg shadow-primary/20"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Drafting Video...
              </>
            ) : (
              <>
                <Sparkles className="w-5 h-5" />
                Generate Draft
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
