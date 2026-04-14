import React, { useState, useEffect } from 'react';
import { Clock } from 'lucide-react';

export default function TopClock() {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    let animationFrameId;
    const updateTime = () => {
      setTime(new Date());
      animationFrameId = requestAnimationFrame(updateTime);
    };
    animationFrameId = requestAnimationFrame(updateTime);
    return () => cancelAnimationFrame(animationFrameId);
  }, []);

  const formatms = (ms) => ms.toString().padStart(3, '0');
  
  const optionsTime = { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true };
  const rawTime = time.toLocaleTimeString(undefined, optionsTime);
  // Split "10:23:45 AM" → time + meridiem
  const [clockTime, meridiem] = rawTime.split(' ');

  const optionsDate = { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' };
  const strDate = time.toLocaleDateString(undefined, optionsDate);

  return (
    <div className="flex items-center gap-2 px-3 py-1 rounded-lg glass text-fgDefault font-mono text-xs">
      <Clock className="w-3.5 h-3.5 text-accent" />
      <div className="flex flex-col items-end leading-none">
        <span className="flex items-baseline gap-1">
          <span className="font-semibold tabular-nums">{clockTime}</span>
          {meridiem && (
            <span className="text-[9px] text-accent font-bold tracking-wider">{meridiem}</span>
          )}
          <span className="text-[9px] text-fgSubtle tabular-nums">.{formatms(time.getMilliseconds())}</span>
        </span>
        <span className="text-[10px] text-fgSubtle tracking-wide mt-0.5">{strDate}</span>
      </div>
    </div>
  );
}
