import React, { useState, useRef } from 'react';
import { Mic, MicOff, Loader2, AlertCircle } from 'lucide-react';

/**
 * VoiceButton
 * Click once to start recording, click again to stop and transcribe.
 * Props:
 *   onTranscript(text: string) — called with transcribed text
 *   disabled?: boolean
 *   className?: string
 */
export default function VoiceButton({ onTranscript, disabled = false, className = '' }) {
  const [state, setState] = useState('idle'); // idle | recording | transcribing | error
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];

      // Pick best supported format
      const mimeType = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/ogg',
      ].find(m => MediaRecorder.isTypeSupported(m)) || '';

      const mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        // Stop mic indicator
        stream.getTracks().forEach(t => t.stop());

        const totalSize = chunksRef.current.reduce((s, c) => s + c.size, 0);
        if (totalSize < 1000) {
          // Nothing was captured — probably less than 0.5s
          setState('idle');
          return;
        }

        setState('transcribing');
        const mType = mimeType || 'audio/webm';
        const blob = new Blob(chunksRef.current, { type: mType });
        const formData = new FormData();
        formData.append('file', blob, 'voice.webm');

        try {
          const res = await fetch('/transcribe', { method: 'POST', body: formData });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const data = await res.json();
          if (data.text && data.text.trim()) {
            onTranscript(data.text.trim());
            setState('idle');
          } else {
            // Got response but empty — show brief error
            setState('error');
            setTimeout(() => setState('idle'), 2000);
          }
        } catch (err) {
          console.error('Transcription failed:', err);
          setState('error');
          setTimeout(() => setState('idle'), 2000);
        }
      };

      // timeslice=200ms: collect data every 200ms so we don't lose audio on abrupt stop
      mediaRecorder.start(200);
      setState('recording');
    } catch (err) {
      console.error('Mic access denied:', err);
      setState('error');
      setTimeout(() => setState('idle'), 2000);
    }
  };

  const stopRecording = () => {
    const mr = mediaRecorderRef.current;
    if (mr && mr.state === 'recording') {
      mr.requestData(); // flush any remaining buffered audio
      mr.stop();
    }
  };

  const handleClick = () => {
    if (state === 'idle') startRecording();
    else if (state === 'recording') stopRecording();
    // ignore clicks during transcribing / error
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={disabled || state === 'transcribing'}
      title={
        state === 'recording' ? 'Click to stop recording'
        : state === 'transcribing' ? 'Transcribing...'
        : state === 'error' ? 'Try again'
        : 'Voice input (click to start)'
      }
      className={`p-2 rounded-md transition-all disabled:opacity-40 disabled:cursor-not-allowed shrink-0 ${
        state === 'recording'
          ? 'bg-red-500/20 border border-red-500/50 text-red-400 shadow-[0_0_12px_rgba(239,68,68,0.4)] animate-pulse'
          : state === 'transcribing'
          ? 'bg-accent/10 border border-accent/30 text-accent'
          : state === 'error'
          ? 'bg-red-900/20 border border-red-500/30 text-red-400'
          : 'text-fgSubtle hover:text-fgDefault hover:bg-canvas/50 border border-transparent hover:border-borderDefault/50'
      } ${className}`}
    >
      {state === 'transcribing' ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : state === 'recording' ? (
        <MicOff className="w-4 h-4" />
      ) : state === 'error' ? (
        <AlertCircle className="w-4 h-4" />
      ) : (
        <Mic className="w-4 h-4" />
      )}
    </button>
  );
}
