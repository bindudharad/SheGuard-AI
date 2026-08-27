import { motion } from 'framer-motion';
import EmptyStateArt from '../assets/emptyState.jsx';

export default function EmptyState() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-[2rem] border border-white/10 bg-white/[0.055] p-8 text-center shadow-panel backdrop-blur-2xl"
    >
      <EmptyStateArt />
      <h2 className="mt-4 text-3xl font-black tracking-tight text-white">No incidents on the wire</h2>
      <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-300">
        SheGuard is listening for verified emergency signals. New incidents will appear here as polished live reports.
      </p>
    </motion.div>
  );
}
