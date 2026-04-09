
import { RotateCcw, CheckCircle2 } from 'lucide-react';

export default function StepResult({ resultData, onReset }) {
  // Extracting from payload mapping
  const videoUrl = resultData?.video_url;

  return (
    <div className="max-w-2xl mx-auto w-full space-y-6">
      <div className="text-center space-y-2">
        <div className="inline-flex items-center justify-center p-3 bg-green-500/20 rounded-2xl mb-4">
          <CheckCircle2 className="w-8 h-8 text-green-500" />
        </div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Synthesis Complete</h1>
        <p className="text-muted-foreground">Your video has been rendered and is ready to view.</p>
      </div>

      <div className="bg-card border border-border p-4 sm:p-8 rounded-2xl shadow-xl shadow-black/50 space-y-6 flex flex-col items-center">
        
        {videoUrl ? (
          <div className="w-[320px] aspect-[9/16] bg-black rounded-lg overflow-hidden border border-border/50 shadow-lg shrink-0">
            <video 
              controls 
              autoPlay 
              className="w-full h-full object-cover"
              src={videoUrl}
            >
              Your browser does not support the video tag.
            </video>
          </div>
        ) : (
          <div className="w-[320px] aspect-[9/16] bg-secondary/20 rounded-lg flex items-center justify-center border border-border/50 text-muted-foreground">
            No video URL provided
          </div>
        )}

        <div className="pt-6 w-full border-t border-border/50 flex justify-center">
          <button 
            onClick={onReset}
            className="px-6 py-2.5 bg-secondary hover:bg-secondary/80 text-foreground rounded-lg font-medium flex items-center justify-center gap-2 transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            Start Over
          </button>
        </div>
      </div>
    </div>
  );
}
