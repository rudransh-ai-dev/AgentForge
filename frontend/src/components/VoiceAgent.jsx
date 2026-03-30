import React, { useState, useRef, useEffect } from 'react';
import { Mic, MicOff, Settings, Volume2, User, Radio, Loader2 } from 'lucide-react';

export default function VoiceAgent() {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [selectedVoice, setSelectedVoice] = useState("NATF2.pt"); // Natural Female 2
  const [transcript, setTranscript] = useState([]);
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      
      mediaRecorderRef.current.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        audioChunksRef.current = [];
        await sendAudioToBackend(audioBlob);
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
      setTranscript(prev => [...prev, { text: "Listening... (Click mic to stop and send)", sender: "system" }]);
    } catch (err) {
      console.error("Mic error:", err);
      alert("Microphone access denied or not available.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      // Stop all mic tracks
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      setIsRecording(false);
    }
  };

  const toggleRecording = () => {
    if (!isRecording) {
      startRecording();
    } else {
      stopRecording();
    }
  };

  const sendAudioToBackend = async (blob) => {
    setIsProcessing(true);
    setTranscript(prev => [...prev, { text: "Processing speech...", sender: "system" }]);
    const formData = new FormData();
    formData.append("audio", blob, "recording.webm");

    try {
      const res = await fetch("http://localhost:8888/api/voice-chat", {
        method: "POST",
        body: formData
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Voice processing failed.");
      }

      const userText = res.headers.get("X-User-Transcript") || "Unintelligible...";
      const agentText = res.headers.get("X-Agent-Transcript") || "I have no words.";

      setTranscript(prev => [
        ...prev.filter(msg => msg.sender !== 'system'),
        { text: decodeURIComponent(userText), sender: "user" },
        { text: decodeURIComponent(agentText), sender: "agent" }
      ]);

      const audioBlob = await res.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      audio.play();

    } catch (err) {
      console.error(err);
      alert(`Backend Error: ${err.message}`);
      setTranscript(prev => [...prev.filter(msg => msg.sender !== 'system'), { text: `Error: ${err.message}`, sender: "system" }]);
    } finally {
      setIsProcessing(false);
    }
  };

  const VOICES = [
    { id: "NATF2.pt", name: "Natural Female" },
    { id: "NATM1.pt", name: "Natural Male" },
    { id: "VARF0.pt", name: "Expressive Female" },
    { id: "VARM2.pt", name: "Expressive Male" },
  ];

  return (
    <div className="flex-1 h-full flex flex-col items-center justify-center bg-[#070709] p-8 overflow-y-auto custom-scrollbar">
      <div className="max-w-4xl w-full">
        <div className="text-center mb-8">
          <div className="relative inline-block mb-4">
            <Radio className={`w-12 h-12 ${isRecording ? 'text-green-400 animate-pulse' : 'text-gray-500'} mx-auto`} />
            {isRecording && (
              <span className="absolute top-0 right-0 w-3 h-3 bg-red-500 rounded-full animate-ping"></span>
            )}
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">PersonaPlex Voice Agent (NVIDIA)</h2>
          <p className="text-sm text-gray-400">Full-duplex real-time conversational agent.</p>
        </div>

        <div className="bg-[#0a0a0f] border border-white/10 p-8 rounded-2xl mb-8 flex flex-col items-center gap-6">
          
          {/* Main Visualizer */}
          <div className="w-full max-w-lg h-48 border border-white/5 bg-black/40 rounded-xl flex items-center justify-center relative overflow-hidden">
            {isProcessing ? (
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="w-10 h-10 text-cyan-400 animate-spin" />
                <span className="text-xs text-cyan-400 animate-pulse">AI is thinking...</span>
              </div>
            ) : isRecording ? (
              <div className="flex gap-2 items-end justify-center h-24">
                {[1, 2, 3, 4, 5, 6, 7].map((bar) => (
                  <div 
                    key={bar} 
                    className="w-3 bg-gradient-to-t from-green-500 to-emerald-400 rounded-t-sm"
                    style={{
                      height: `${20 + Math.random() * 80}%`,
                      animation: `bounce ${0.5 + Math.random()}s infinite alternate`
                    }}
                  ></div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center opacity-30">
                <MicOff className="w-12 h-12 text-white mb-2" />
                <span className="text-sm">Microphone Off</span>
              </div>
            )}
          </div>

          {/* Controls */}
          <div className="flex items-center gap-6 w-full max-w-lg">
            <div className="flex-1 flex flex-col gap-2">
              <label className="text-xs text-gray-500 uppercase tracking-widest font-bold">Select Voice</label>
              <select 
                value={selectedVoice}
                onChange={(e) => setSelectedVoice(e.target.value)}
                disabled={isRecording}
                className="bg-white/5 border border-white/10 rounded-lg p-3 text-sm text-white outline-none focus:border-green-500/50 disabled:opacity-50"
              >
                {VOICES.map((v) => (
                  <option key={v.id} value={v.id} className="bg-[#080810] text-gray-200">{v.name}</option>
                ))}
              </select>
            </div>
            
            <button
              onClick={toggleRecording}
              disabled={isProcessing}
              className={`mt-6 w-20 h-20 rounded-full flex items-center justify-center shadow-lg transition-all disabled:opacity-30 disabled:cursor-not-allowed ${
                isRecording 
                  ? 'bg-red-500/20 text-red-500 border border-red-500/50 hover:bg-red-500/30 hover:scale-105'
                  : 'bg-green-500/20 text-green-400 border border-green-500/50 hover:bg-green-500/30 hover:scale-105'
              }`}
            >
              {isProcessing ? <Loader2 className="w-8 h-8 animate-spin" /> : isRecording ? <MicOff className="w-8 h-8" /> : <Mic className="w-8 h-8 ml-1" />}
            </button>
          </div>

        </div>

        {/* Live Transcript Log */}
        <div className="bg-[#0a0a0f] border border-white/10 rounded-2xl flex flex-col overflow-hidden h-64">
          <div className="bg-white/5 p-3 border-b border-white/10 flex items-center justify-between">
            <h3 className="text-xs text-gray-400 uppercase tracking-widest font-bold">Live Transcript</h3>
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${isRecording ? 'bg-green-500' : 'bg-gray-600'}`}></span>
              <span className="text-xs text-gray-500">{isRecording ? 'Connected' : 'Offline'}</span>
            </div>
          </div>
          <div className="flex-1 p-4 overflow-y-auto flex flex-col gap-3 font-mono text-sm">
            {transcript.length === 0 && (
              <span className="text-gray-600 italic">Conversation logs will appear here...</span>
            )}
            {transcript.map((msg, i) => (
              <div key={i} className={`flex ${msg.sender === 'agent' ? 'justify-start' : msg.sender === 'user' ? 'justify-end' : 'justify-center'}`}>
                <div className={`
                  px-3 py-1.5 rounded-lg max-w-[80%]
                  ${msg.sender === 'agent' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 
                    msg.sender === 'user' ? 'bg-white/10 text-white' : 
                    'text-gray-500 text-xs italic bg-transparent'}
                `}>
                  {msg.text}
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}
