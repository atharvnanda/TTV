import { useState, useRef, useEffect } from 'react';

import { Loader2, Clapperboard, FileText, Image as ImageIcon, Clock } from 'lucide-react';

export default function StepReview({ draftData, onProduceComplete }) {
  const [loading, setLoading] = useState(false);
  const [script, setScript] = useState(draftData?.draft?.script || '');
  const [brollPrompts, setBrollPrompts] = useState(draftData?.draft?.broll_prompts || []);

  const handlePromptChange = (index, val) => {
    const newPrompts = [...brollPrompts];
    newPrompts[index] = val;
    setBrollPrompts(newPrompts);
  };

  const handleProduce = async () => {
    setLoading(true);

    try {
      // Data Contract payload
      const payload = {
        edited_script: script,
        edited_broll_prompts: brollPrompts,
        scraped_images: draftData?.draft?.scraped_images || [],
        tts_provider: 'elevenlabs',
        image_provider: 'gemini',
        lang: draftData?.draft?.lang || 'en',
      };

      const response = await fetch('http://localhost:8000/api/produce', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error('Production failed');
      }

      const resJson = await response.json();
      if (resJson.status === 'success') {
        onProduceComplete({ video_url: resJson.video_url });
      }
    } catch (err) {
      console.error(err);
      alert("Error reaching backend. Is localhost:8000/api/produce running?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto w-full space-y-6">
      <div className="text-center space-y-2">
        <div className="inline-flex items-center justify-center p-3 bg-accent/20 rounded-2xl mb-4">
          <Clapperboard className="w-8 h-8 text-primary" />
        </div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Review & Edit</h1>
        <p className="text-muted-foreground">Fine-tune the narrative before rendering.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 bg-card border border-border p-6 rounded-2xl shadow-xl shadow-black/50">
        
        {/* Script Editor */}
        <div className="flex flex-col space-y-3">
          <div className="flex items-center gap-2 font-semibold text-foreground pb-2 border-b border-border/50">
            <FileText className="w-4 h-4 text-primary" />
            <span>Spoken Script</span>
          </div>
          <textarea 
            value={script}
            onChange={(e) => setScript(e.target.value)}
            className="flex-1 min-h-[300px] w-full bg-secondary/20 p-4 border-none focus:ring-1 focus:ring-primary/50 text-foreground resize-none leading-relaxed transition-all"
          />
        </div>

        {/* B-Roll Prompts */}
        <div className="flex flex-col space-y-3">
          <div className="flex items-center gap-2 font-semibold text-foreground pb-2 border-b border-border/50">
            <ImageIcon className="w-4 h-4 text-primary" />
            <span>Visual Prompts</span>
          </div>
          <div className="flex-1 overflow-y-auto space-y-3 pr-2 scrollbar-thin">
            {brollPrompts.map((prompt, i) => (
              <div key={i} className="flex flex-col gap-1">
                <label className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider ml-1">Shot {i + 1}</label>
                <input 
                  type="text" 
                  value={prompt}
                  onChange={(e) => handlePromptChange(i, e.target.value)}
                  className="w-full bg-secondary/20 p-3 border-none focus:ring-1 focus:ring-primary/50 text-sm transition-all text-foreground"
                />
              </div>
            ))}
          </div>
        </div>

      </div>

      <div className="flex flex-col sm:flex-row items-center justify-end gap-4 pt-4">
        {/* Estimated Time Callout */}
        <div className="flex items-center gap-2 px-4 py-2 bg-yellow-400/10 border border-yellow-400/20 rounded-lg">
          <Clock className="w-4 h-4 text-yellow-500" />
          <span className="text-sm font-medium text-yellow-500/90">
            Est. Generation: {getEstimate(draftData?.settings?.duration)}
          </span>
        </div>

        <button 
          onClick={handleProduce}
          disabled={loading || !script.trim()}
          className="w-full sm:w-auto px-8 py-3.5 bg-primary hover:bg-primaryHover text-primary-foreground rounded-lg font-semibold flex items-center justify-center gap-2 disabled:opacity-50 transition-all shadow-lg shadow-primary/20"
        >
          {loading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Producing Video... This might take a minute
            </>
          ) : (
            <>
              <Clapperboard className="w-5 h-5" />
              Produce Final Video
            </>
          )}
        </button>
      </div>
    </div>
  );
}

// Map duration to estimate strings
function getEstimate(duration) {
  const estimates = {
    '20-25': '35–40 seconds',
    '45-50': '1 min to 1 min 15s',
    '60':    '1 min 15s to 1 min 35s',
    '90':    '1 min 45s to 2 min 5s',
    '120':   '2 min 15s to 2 min 35s'
  };
  return estimates[duration] || 'Around 1-2 minutes';
}
