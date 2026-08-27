import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Bell, AlertTriangle, MapPin, Zap, UserPlus, CheckCircle2 } from 'lucide-react';
import { formatTime } from '../lib/incidents';

const notificationIcons = {
  new_emergency: { icon: UserPlus, color: 'text-red-400', bg: 'bg-red-500/20 border-red-500/30' },
  threat_escalation: { icon: AlertTriangle, color: 'text-amber-400', bg: 'bg-amber-500/20 border-amber-500/30' },
  tracking_lost: { icon: MapPin, color: 'text-red-400', bg: 'bg-red-500/20 border-red-500/30' },
  cctv_offline: { icon: Zap, color: 'text-orange-400', bg: 'bg-orange-500/20 border-orange-500/30' },
  ai_detection: { icon: AlertTriangle, color: 'text-violet-400', bg: 'bg-violet-500/20 border-violet-500/30' },
  new_evidence: { icon: Bell, color: 'text-blue-400', bg: 'bg-blue-500/20 border-blue-500/30' },
  emergency_resolved: { icon: CheckCircle2, color: 'text-emerald-400', bg: 'bg-emerald-500/20 border-emerald-500/30' },
  default: { icon: Bell, color: 'text-slate-400', bg: 'bg-white/10 border-white/20' },
};

export default function NotificationCenter({ notifications = [], onClose, onNotificationClick }) {
  const handleClickOutside = (event) => {
    if (event.target.closest('.notification-center')) return;
    onClose?.();
  };

  useEffect(() => {
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  if (notifications.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 10 }}
        className='absolute right-0 top-full mt-2 w-80 rounded-xl border border-white/10 bg-command-950/95 backdrop-blur-2xl shadow-xl z-50'
      >
        <div className='p-6 text-center text-slate-400'>
          <Bell className='h-10 w-10 mx-auto mb-3 text-slate-600' />
          <p>No notifications</p>
          <p className='text-xs mt-1'>You are all caught up</p>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 10 }}
      className='notification-center absolute right-0 top-full mt-2 w-80 max-h-[500px] overflow-hidden rounded-xl border border-white/10 bg-command-950/95 backdrop-blur-2xl shadow-xl z-50'
    >
      <div className='flex items-center justify-between border-b border-white/10 px-4 py-3'>
        <h3 className='text-sm font-bold text-white flex items-center gap-2'>
          <Bell className='h-4 w-4 text-alert-500' />
          Notifications
          {notifications.length > 0 && (
            <span className='text-xs font-black text-white px-2 py-0.5 rounded-full bg-alert-500/20 border border-alert-500/30'>
              {notifications.length}
            </span>
          )}
        </h3>
        <button
          onClick={onClose}
          className='flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition'
        >
          <X className='h-4 w-4' />
        </button>
      </div>

      <div className='max-h-[400px] overflow-y-auto thin-scrollbar'>
        {notifications.map((notification, index) => (
          <motion.div
            key={notification.id || index}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ delay: index * 0.03 }}
            onClick={() => {
              onNotificationClick?.(notification);
              onClose?.();
            }}
            className='relative px-4 py-3 border-b border-white/5 hover:bg-white/5 cursor-pointer transition group'
          >
            <div className='flex items-start gap-3'>
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border">
                {(() => {
                const Icon = notificationIcons[notification.type]?.icon || notificationIcons.default.icon;
                return <Icon className="h-5 w-5" />;
              })()}
              </div>
              <div className='flex-1 min-w-0'>
                <p className='text-sm font-medium text-white'>{notification.message}</p>
                <p className='text-xs text-slate-500 mt-0.5'>{formatTime(notification.timestamp)}</p>
                {notification.sessionId && (
                  <p className='text-xs text-slate-400 mt-0.5 font-mono'>Session: {notification.sessionId}</p>
                )}
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {notifications.length > 5 && (
        <div className='border-t border-white/10 px-4 py-3 text-center'>
          <p className='text-xs text-slate-500'>Showing latest {Math.min(5, notifications.length)} of {notifications.length} notifications</p>
        </div>
      )}
    </motion.div>
  );
}
