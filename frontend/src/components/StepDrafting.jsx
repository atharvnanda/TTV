import { useState } from 'react';

import { Loader2, Sparkles, Clock, AlignLeft, Type, Video, Link as LinkIcon, Image as ImageIcon } from 'lucide-react';
import clsx from 'clsx';

const DURATION_OPTIONS = [
  { value: '20-25', label: '20–25 sec', words: '65', range: '50-65' },
  { value: '45-50', label: '45–50 sec', words: '130', range: '110-130' },
  { value: '60',    label: '60 sec',      words: '160', range: '150-160' },
  { value: '90',    label: '90 sec',      words: '240', range: '210-240' },
  { value: '120',   label: '2 min',       words: '320', range: '280-320' },
];

export default function StepDrafting({ onDraftComplete }) {
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState('topic'); // 'topic' | 'text' | 'url'
  const [content, setContent] = useState('');
  const [duration, setDuration] = useState('20-25');
  const [uploadedImages, setUploadedImages] = useState([]);

  const IMAGE_LIMITS = {
    '20-25': 3,
    '45-50': 4,
    '60': 5,
    '90': 5,
    '120': 6
  };
  const maxImg = IMAGE_LIMITS[duration] || 3;
  const isOverLimit = uploadedImages.length > maxImg;

  const handleImageUpload = (e) => {
    const files = Array.from(e.target.files);
    files.forEach(file => {
      const reader = new FileReader();
      reader.onloadend = () => {
        setUploadedImages(prev => [...prev, reader.result]);
      };
      reader.readAsDataURL(file);
    });
  };

  const handleGenerate = async () => {
    if (!content.trim() || isOverLimit) return;
    setLoading(true);

    const selectedDuration = DURATION_OPTIONS.find(d => d.value === duration);

    try {
      const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
      const response = await fetch(`${API_BASE_URL}/api/draft`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          input_mode: mode === 'text' ? 'direct_text' : mode,
          content: content,
          niche: 'general',
          llm_provider: 'groq',
          image_provider: 'gemini',
          tts_provider: 'elevenlabs',
          target_words: selectedDuration?.words || '180-200',
          uploaded_images: uploadedImages,
        })
      });

      if (!response.ok) {
        throw new Error('Drafting failed');
      }

      const resJson = await response.json();
      if (resJson.status === 'success') {
        onDraftComplete({
          draft: resJson.data,
          settings: {
            niche: 'general',
            llmProvider: 'groq',
            imageProvider: 'gemini',
            ttsProvider: 'elevenlabs',
            duration: duration,
          }
        });
      }
    } catch (err) {
      console.error(err);
      alert("Error reaching backend.");
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
        <p className="text-muted-foreground">Choose your input, set a duration, and ignite the creative process.</p>
      </div>

      <div className="bg-card border border-border p-6 rounded-2xl shadow-xl shadow-black/50 space-y-5">
        
        {/* Top row: Input mode tabs + Duration selector */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex bg-secondary/30 p-1 rounded-lg border border-border shrink-0">
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

          {/* Duration Selector */}
          <div className="flex items-center gap-2 shrink-0">
            <Clock className="w-4 h-4 text-primary" />
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Duration</label>
            <select 
              className="w-auto min-w-[140px]" 
              value={duration} 
              onChange={e => setDuration(e.target.value)}
            >
              {DURATION_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>
                  {opt.label} ({opt.range} words)
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Input area */}
        <div className="min-h-[200px] flex flex-col relative group">
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

        {/* Image Upload for Text and URL Mode */}
        {(mode === 'text' || mode === 'url') && (
          <div className="space-y-3 pt-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-semibold text-foreground flex items-center gap-2">
                <ImageIcon className="w-4 h-4 text-primary" />
                Upload Background Images (Optional)
              </label>
              <span className={clsx(
                "text-xs font-medium px-2 py-0.5 rounded-full",
                isOverLimit ? "bg-red-500/10 text-red-500" : "bg-primary/10 text-primary"
              )}>
                {uploadedImages.length} / {maxImg} images
              </span>
            </div>
            
            <input 
              type="file" 
              multiple 
              accept="image/*"
              onChange={handleImageUpload}
              className="w-full text-sm text-muted-foreground file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-primary/10 file:text-primary hover:file:bg-primary/20"
            />

            {isOverLimit && (
              <div className="p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg flex items-start gap-2">
                <div className="mt-0.5 text-yellow-500 text-sm">⚠️</div>
                <p className="text-xs text-yellow-600 font-medium">
                  You have exceeded the number of images for this duration. Only upload {maxImg} images.
                </p>
              </div>
            )}
            
            {uploadedImages.length > 0 && (
              <div className="flex flex-col gap-2">
                <div className="flex flex-wrap gap-3">
                  {uploadedImages.map((img, idx) => (
                    <div key={idx} className="relative w-16 h-16 rounded-md overflow-hidden border border-border group/img">
                      <img src={img} alt={`Upload ${idx}`} className="w-full h-full object-cover" />
                      <button 
                        onClick={() => {
                          const newImgs = [...uploadedImages];
                          newImgs.splice(idx, 1);
                          setUploadedImages(newImgs);
                        }}
                        className="absolute top-1 right-1 bg-black/60 text-white p-1 rounded-full opacity-0 group-hover/img:opacity-100 transition-opacity hover:bg-red-500"
                        title="Remove image"
                      >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
                <button 
                  onClick={() => setUploadedImages([])}
                  className="text-[10px] uppercase tracking-widest font-bold text-muted-foreground hover:text-red-500 transition-colors self-start"
                >
                  Clear all uploads
                </button>
              </div>
            )}
          </div>
        )}

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
  );
}
