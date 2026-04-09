import { useState } from 'react';

import StepDrafting from './components/StepDrafting';
import StepReview from './components/StepReview';
import StepResult from './components/StepResult';

export default function App() {
  const [step, setStep] = useState('drafting'); // 'drafting' | 'review' | 'result'
  
  // State to hold data passed between steps
  const [draftData, setDraftData] = useState(null); 
  const [resultData, setResultData] = useState(null);

  const handleDraftComplete = (data) => {
    setDraftData(data);
    setStep('review');
  };

  const handleProduceComplete = (data) => {
    setResultData(data);
    setStep('result');
  };

  const handleReset = () => {
    setDraftData(null);
    setResultData(null);
    setStep('drafting');
  };

  return (
    <main className="min-h-screen bg-background text-foreground flex flex-col p-4 sm:p-8 font-sans selection:bg-primary/30">
      
      {/* Top Navigation / Brand indicator */}
      <header className="mb-12 w-full max-w-5xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-primary to-blue-500 shadow-md shadow-primary/20" />
          <span className="font-bold tracking-tight text-xl">VideoPipeline</span>
        </div>
        <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <span className={step === 'drafting' ? 'text-primary font-bold' : ''}>Configure</span>
          <span>→</span>
          <span className={step === 'review' ? 'text-primary font-bold' : ''}>Review</span>
          <span>→</span>
          <span className={step === 'result' ? 'text-primary font-bold' : ''}>Result</span>
        </div>
      </header>

      <div className="flex-1 w-full max-w-5xl mx-auto relative flex items-start justify-center">
          {step === 'drafting' && (
            <StepDrafting key="drafting" onDraftComplete={handleDraftComplete} />
          )}
          {step === 'review' && (
            <StepReview key="review" draftData={draftData} onProduceComplete={handleProduceComplete} />
          )}
          {step === 'result' && (
            <StepResult key="result" resultData={resultData} onReset={handleReset} />
          )}
      </div>

    </main>
  );
}
