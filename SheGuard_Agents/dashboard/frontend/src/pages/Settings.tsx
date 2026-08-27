import * as React from "react";

export function Settings() {
  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">Settings</h2>
      <div className="bg-bg-card rounded-2xl border border-slate-800/50 p-6 space-y-6">
        <div>
          <h3 className="font-medium text-slate-200 mb-2">Dashboard Configuration</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-900/40 border border-slate-800/50">
              <div>
                <p className="text-sm text-slate-200">Refresh Rate</p>
                <p className="text-xs text-slate-500">How often to poll for new data</p>
              </div>
              <select className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-sm text-slate-200">
                <option value="2000">2 seconds</option>
                <option value="5000" selected>5 seconds</option>
                <option value="10000">10 seconds</option>
              </select>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-900/40 border border-slate-800/50">
              <div>
                <p className="text-sm text-slate-200">Reduce Motion</p>
                <p className="text-xs text-slate-500">Minimize animations for accessibility</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" className="sr-only peer" />
                <div className="w-9 h-5 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-sky-600"></div>
              </label>
            </div>
          </div>
        </div>
        <div>
          <h3 className="font-medium text-slate-200 mb-2">Security</h3>
          <p className="text-xs text-slate-500">No sensitive data is stored in the browser.</p>
        </div>
      </div>
    </div>
  );
}
