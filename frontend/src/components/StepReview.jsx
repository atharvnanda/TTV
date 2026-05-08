import { useState, useRef, useEffect } from 'react';

import { Loader2, Clapperboard, FileText, Image as ImageIcon, Clock } from 'lucide-react';

export default function StepReview({ draftData, onProduceComplete }) {
  const [loading, setLoading] = useState(false);
  const [script, setScript] = useState(draftData?.draft?.script || '');
  const [brollPrompts, setBrollPrompts] = useState(draftData?.draft?.broll_prompts || []);
  const [reviewImages, setReviewImages] = useState([
    ...(draftData?.draft?.scraped_images || []),
    ...(draftData?.draft?.uploaded_images || [])
  ]);

  const IMAGE_LIMITS = {
    '20-25': 3,
    '45-50': 4,
    '60': 5,
    '90': 5,
    '120': 6
  };
  const duration = draftData?.settings?.duration || '20-25';
  const maxImg = IMAGE_LIMITS[duration] || 3;
  const isOverLimit = reviewImages.length > maxImg;

  const handleImageUpload = (e) => {
    const files = Array.from(e.target.files);
    files.forEach(file => {
      const reader = new FileReader();
      reader.onloadend = () => {
        setReviewImages(prev => [...prev, reader.result]);
      };
      reader.readAsDataURL(file);
    });
  };

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
        review_images: reviewImages,
        tts_provider: 'elevenlabs',
        image_provider: 'gemini',
        lang: draftData?.draft?.lang || 'en',
        duration: duration,
      };

      const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
      const response = await fetch(`${API_BASE_URL}/api/produce`, {
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
      alert("Error reaching backend.");
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

        {/* Review Images */}
        <div className="flex flex-col space-y-3 lg:col-span-2">
          <div className="flex items-center justify-between font-semibold text-foreground pb-2 border-b border-border/50">
            <div className="flex items-center gap-2">
              <ImageIcon className="w-4 h-4 text-primary" />
              <span>Visual Assets</span>
              <span className="text-xs font-normal text-muted-foreground ml-2">
                (Used before generating AI b-roll)
              </span>
            </div>
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${isOverLimit ? "bg-red-500/10 text-red-500" : "bg-primary/10 text-primary"}`}>
              {reviewImages.length} / {maxImg} images
            </span>
          </div>
          
          <div className="space-y-4 pt-1">
            {reviewImages.length > 0 && (
              <div className="flex flex-wrap gap-4">
                {reviewImages.map((img, idx) => (
                  <div key={idx} className="relative w-24 h-24 sm:w-32 sm:h-32 rounded-lg overflow-hidden border border-border group/img shadow-sm">
                    <img src={img} alt={`Asset ${idx}`} className="w-full h-full object-cover" />
                    <button 
                      onClick={() => {
                        const newImgs = [...reviewImages];
                        newImgs.splice(idx, 1);
                        setReviewImages(newImgs);
                      }}
                      className="absolute top-1.5 right-1.5 bg-black/60 text-white p-1 rounded-full opacity-0 group-hover/img:opacity-100 transition-opacity hover:bg-red-500"
                      title="Remove image"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            )}
            
            <div className="pt-2">
              <input 
                type="file" 
                multiple 
                accept="image/*"
                onChange={handleImageUpload}
                className="w-full text-sm text-muted-foreground file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-primary/10 file:text-primary hover:file:bg-primary/20"
              />
              {isOverLimit && (
                <div className="mt-3 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg flex items-start gap-2 max-w-md">
                  <div className="mt-0.5 text-yellow-500 text-sm">⚠️</div>
                  <p className="text-xs text-yellow-600 font-medium">
                    You have exceeded the optimal number of images. Only {maxImg} will be used.
                  </p>
                </div>
              )}
            </div>
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
