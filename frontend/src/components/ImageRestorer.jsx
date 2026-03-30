import React, { useState } from 'react';
import { Upload, Image as ImageIcon, Sparkles, Loader2, Download } from 'lucide-react';

export default function ImageRestorer() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewSize, setPreviewSize] = useState({ width: 0, height: 0 });
  const [isProcessing, setIsProcessing] = useState(false);
  const [resultImage, setResultImage] = useState(null);
  const [prompt, setPrompt] = useState('Please deblur the image and make it sharper');

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      const imageUrl = URL.createObjectURL(file);
      setSelectedFile({ file, url: imageUrl });
      
      const img = new Image();
      img.onload = () => {
        setPreviewSize({ width: img.width, height: img.height });
      };
      img.src = imageUrl;
      setResultImage(null);
    }
  };

  const handleProcess = async () => {
    if (!selectedFile) return;

    setIsProcessing(true);
    const formData = new FormData();
    formData.append('image', selectedFile.file);
    formData.append('prompt', prompt);

    try {
      const response = await fetch('http://127.0.0.1:8888/api/restore-image', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Failed to process image');
      }

      const blob = await response.blob();
      setResultImage(URL.createObjectURL(blob));
    } catch (error) {
      console.error('Error processing image:', error);
      alert(`Backend Error: ${error.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDownload = () => {
    if (!resultImage) return;
    const a = document.createElement('a');
    a.href = resultImage;
    a.download = 'restored-image.png';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const PROMPT_OPTIONS = [
    { label: 'Deblur', value: 'Please deblur the image and make it sharper' },
    { label: 'Remove Artifacts', value: 'Please restore the image clarity and artifacts.' },
    { label: 'Dehaze', value: 'Please dehaze the image' },
    { label: 'Low-light Enhance', value: 'Please restore this low-quality image, recovering its normal brightness and clarity.' },
    { label: 'Denoise', value: 'Please remove noise from the image.' },
  ];

  // If the current prompt doesn't match a preset exactly, it's considered "Custom"
  const isCustom = !PROMPT_OPTIONS.some(opt => opt.value === prompt);

  return (
    <div className="flex-1 h-full flex flex-col items-center justify-center bg-[#070709] p-8 overflow-y-auto custom-scrollbar">
      <div className="max-w-4xl w-full">
        <div className="text-center mb-8">
          <Sparkles className="w-10 h-10 text-cyan-400 mx-auto mb-4 opacity-80" />
          <h2 className="text-2xl font-bold text-white mb-2">RealRestorer AI</h2>
          <p className="text-sm text-gray-400">Upload a degraded image to restore it using RealRestorer.</p>
        </div>

        <div className="bg-[#0a0a0f] border border-white/10 p-6 rounded-2xl mb-8 flex flex-col gap-6">
          {/* Controls */}
          <div className="flex items-center gap-4">
            <select 
              value={isCustom ? "custom" : prompt} 
              onChange={(e) => {
                if (e.target.value === "custom") {
                  setPrompt(""); // Clear the text box so they can type
                } else {
                  setPrompt(e.target.value);
                }
              }}
              className="flex-[1.5] bg-white/5 border border-white/10 rounded-lg p-3 text-sm text-gray-200 outline-none focus:border-cyan-500/50"
            >
              <option value="custom" className="bg-[#0a0a0f] text-cyan-400">✏️ Custom Edit...</option>
              {PROMPT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value} className="bg-[#0a0a0f]">{opt.label}</option>
              ))}
            </select>
            <input 
              type="text" 
              value={prompt} 
              onChange={(e) => setPrompt(e.target.value)}
              className="flex-[2.5] bg-white/5 border border-white/10 rounded-lg p-3 text-sm text-gray-200 outline-none focus:border-cyan-500/50 placeholder-gray-600 font-mono"
              placeholder="E.g., Make my red car white..."
            />
          </div>

          {/* Upload Area */}
          <div className="flex gap-6 h-80">
            <div className="flex-1 border-2 border-dashed border-white/10 rounded-xl flex flex-col items-center justify-center p-4 relative overflow-hidden bg-black/20 hover:bg-white/5 transition-colors cursor-pointer" onClick={() => document.getElementById('image-upload').click()}>
              <input 
                id="image-upload" 
                type="file" 
                accept="image/*" 
                className="hidden" 
                onChange={handleFileSelect}
              />
              {selectedFile ? (
                <img src={selectedFile.url} alt="Original" className="w-full h-full object-contain" />
              ) : (
                <>
                  <Upload className="w-8 h-8 text-gray-500 mb-3" />
                  <span className="text-sm text-gray-400">Click to upload original image</span>
                </>
              )}
            </div>

            <div className="flex-1 border border-white/10 rounded-xl flex flex-col items-center justify-center p-4 relative overflow-hidden bg-[#050508]">
              {isProcessing ? (
                <div className="flex flex-col items-center gap-3">
                  <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
                  <span className="text-xs text-gray-400 animate-pulse">Running Diffusion Model...</span>
                </div>
              ) : resultImage ? (
                <div className="relative w-full h-full flex flex-col">
                  <img src={resultImage} alt="Restored" className="flex-1 w-full h-full object-contain" />
                  <button 
                    onClick={handleDownload}
                    className="absolute bottom-2 right-2 bg-black/50 hover:bg-black/80 p-2 rounded-lg border border-white/10 text-white transition-colors flex items-center gap-2"
                  >
                    <Download className="w-4 h-4" /> <span className="text-xs">Save</span>
                  </button>
                </div>
              ) : (
                <>
                  <ImageIcon className="w-8 h-8 text-gray-800 mb-3" />
                  <span className="text-sm text-gray-600">Restored result will appear here</span>
                </>
              )}
            </div>
          </div>
          
          <div className="flex justify-center mt-2">
            <button
              onClick={handleProcess}
              disabled={!selectedFile || isProcessing}
              className="px-8 py-3 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold tracking-wide shadow-[0_0_15px_rgba(6,182,212,0.4)] disabled:opacity-50 disabled:shadow-none disabled:cursor-not-allowed transition-all"
            >
              {isProcessing ? 'Processing Image...' : 'Restore Image'}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
