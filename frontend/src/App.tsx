import React, { useState } from 'react';
import { Header } from './components/Header';
import { ResearchForm } from './components/ResearchForm';
import { ResearchProcess } from './components/ResearchProcess';
import { useDarkMode } from './hooks/useDarkMode';
import { cn } from './lib/utils';

interface FormData {
  companyName: string;
  website: string;
  industry: string;
  headquarters: string;
}

function App() {
  const { darkMode, toggleDarkMode } = useDarkMode();
  const [formData, setFormData] = useState<FormData>({
    companyName: '',
    website: '',
    industry: '',
    headquarters: ''
  });
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsProcessing(true);
    setCurrentStep(0);
    
    try {
      const response = await fetch('http://localhost:5000/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });
      
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const data = await response.json();
      
      // Process each step
      const steps = Object.keys(data.steps);
      for (let i = 0; i < steps.length; i++) {
        await new Promise(resolve => setTimeout(resolve, 2000)); // Delay for visual effect
        setCurrentStep(i + 1);
      }
    } catch (error) {
      console.error('Error processing request:', error);
      // Handle error state
    }
  };

  const handleReset = () => {
    setIsProcessing(false);
    setCurrentStep(0);
    setFormData({
      companyName: '',
      website: '',
      industry: '',
      headquarters: ''
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleFormChange = (data: Partial<FormData>) => {
    setFormData(prev => ({ ...prev, ...data }));
  };

  return (
    <div className={cn(
      "min-h-screen transition-colors duration-200",
      darkMode 
        ? "bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white" 
        : "bg-gradient-to-br from-blue-50 to-indigo-50 text-gray-900"
    )}>
      <div className="container mx-auto px-4 py-8">
        <Header darkMode={darkMode} onDarkModeToggle={toggleDarkMode} />
        
        <ResearchForm
          formData={formData}
          isProcessing={isProcessing}
          darkMode={darkMode}
          onSubmit={handleSubmit}
          onFormChange={handleFormChange}
        />

        <ResearchProcess 
          isActive={isProcessing} 
          currentStep={currentStep} 
          darkMode={darkMode}
          onReset={handleReset}
        />
      </div>
    </div>
  );
}

export default App;