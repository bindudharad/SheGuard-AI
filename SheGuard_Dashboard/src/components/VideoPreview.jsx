import { Play, Video } from 'lucide-react';
import { useRef } from 'react';

export default function VideoPreview({ incident, className = '' }) {
  const videoRef = useRef(null);
  const hasVideo = Boolean(incident.videoUrl);
  const hasImage = Boolean(incident.thumbnailUrl);

  const play = () => {
    if (videoRef.current) {
      videoRef.current.play().catch(() => {});
    }
  };

  const pause = () => {
    if (videoRef.current) {
      videoRef.current.pause();
      videoRef.current.currentTime = 0;
    }
  };

  return (
    <div className={`relative overflow-hidden bg-command-900 ${className}`} onMouseEnter={play} onMouseLeave={pause}>
      {hasVideo ? (
        <video
          ref={videoRef}
          src={incident.videoUrl}
          poster={incident.thumbnailUrl}
          muted
          playsInline
          loop
          preload="metadata"
          className="h-full w-full object-cover transition duration-700 group-hover:scale-105"
        />
      ) : hasImage ? (
        <img src={incident.thumbnailUrl} alt={incident.title} className="h-full w-full object-cover transition duration-700 group-hover:scale-105" />
      ) : (
        <div className="flex h-full min-h-[280px] items-center justify-center bg-[radial-gradient(circle_at_center,rgba(255,49,72,.18),transparent_55%)] text-slate-500">
          <Video className="h-14 w-14" />
        </div>
      )}
      <div className="absolute inset-0 bg-gradient-to-t from-black/78 via-black/10 to-black/10" />
      {hasVideo && (
        <div className="absolute left-4 top-4 flex h-11 w-11 items-center justify-center rounded-full border border-white/20 bg-black/38 text-white backdrop-blur-xl">
          <Play className="ml-0.5 h-5 w-5 fill-white" />
        </div>
      )}
    </div>
  );
}
