import { Building, Globe, Briefcase, MapPin } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '../lib/utils';

interface FormData {
  companyName: string;
  website: string;
  industry: string;
  headquarters: string;
}

interface ResearchFormProps {
  formData: FormData;
  isProcessing: boolean;
  darkMode: boolean;
  onSubmit: (e: React.FormEvent) => Promise<void>;
  onFormChange: (data: Partial<FormData>) => void;
}

export function ResearchForm({ 
  formData, 
  isProcessing, 
  darkMode, 
  onSubmit, 
  onFormChange 
}: ResearchFormProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "max-w-2xl mx-auto rounded-xl p-6 mb-8 backdrop-blur-lg shadow-xl",
        darkMode 
          ? "bg-gray-800/70 border border-gray-700" 
          : "bg-white/80 border border-gray-200"
      )}
    >
      <h1 className={cn(
        "text-3xl font-bold mb-6 text-center",
        darkMode ? "text-white" : "text-gray-800"
      )}>
        Company Research Assistant
      </h1>
      
      <form onSubmit={onSubmit} className="space-y-4">
        <FormField
          icon={Building}
          label="Company Name *"
          type="text"
          required
          value={formData.companyName}
          onChange={(value) => onFormChange({ companyName: value })}
          placeholder="Enter company name"
          darkMode={darkMode}
        />

        <FormField
          icon={Globe}
          label="Website (Optional)"
          type="url"
          value={formData.website}
          onChange={(value) => onFormChange({ website: value })}
          placeholder="https://example.com"
          darkMode={darkMode}
        />

        <FormField
          icon={Briefcase}
          label="Industry (Optional)"
          type="text"
          value={formData.industry}
          onChange={(value) => onFormChange({ industry: value })}
          placeholder="e.g., Technology, Healthcare"
          darkMode={darkMode}
        />

        <FormField
          icon={MapPin}
          label="Headquarters (Optional)"
          type="text"
          value={formData.headquarters}
          onChange={(value) => onFormChange({ headquarters: value })}
          placeholder="e.g., San Francisco, CA"
          darkMode={darkMode}
        />

        <button
          type="submit"
          disabled={isProcessing}
          className={cn(
            "w-full py-3 px-4 rounded-md text-white font-medium transition-colors",
            isProcessing
              ? "bg-gray-400 cursor-not-allowed"
              : darkMode
                ? "bg-blue-600 hover:bg-blue-700"
                : "bg-blue-600 hover:bg-blue-700"
          )}
        >
          {isProcessing ? 'Processing...' : 'Start Research'}
        </button>
      </form>
    </motion.div>
  );
}

interface FormFieldProps {
  icon: React.ElementType;
  label: string;
  type: string;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  required?: boolean;
  darkMode: boolean;
}

function FormField({
  icon: Icon,
  label,
  type,
  value,
  onChange,
  placeholder,
  required,
  darkMode
}: FormFieldProps) {
  return (
    <div className="space-y-2">
      <label className={cn(
        "flex items-center text-sm font-medium",
        darkMode ? "text-gray-300" : "text-gray-700"
      )}>
        <Icon className="w-4 h-4 mr-2" />
        {label}
      </label>
      <input
        type={type}
        required={required}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={cn(
          "w-full px-4 py-2 rounded-md transition-colors duration-200",
          darkMode 
            ? "bg-gray-700/50 border-gray-600 focus:border-blue-500 text-white placeholder-gray-400" 
            : "bg-white/50 border-gray-300 focus:border-blue-500 text-gray-900 placeholder-gray-500",
          "focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 focus:border-transparent"
        )}
        placeholder={placeholder}
      />
    </div>
  );
}