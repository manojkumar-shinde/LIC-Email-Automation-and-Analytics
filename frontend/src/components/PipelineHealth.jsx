import React from 'react';
import { Activity } from 'lucide-react';

const PipelineHealth = ({ isIngesting }) => {
    return (
        <div className="tile-transparent p-6 rounded-xl mb-8 flex items-center justify-between">
            <div className="flex items-center space-x-4">
                <Activity className={`w-6 h-6 ${isIngesting ? 'text-emerald-400 animate-pulse' : 'text-blue-400'}`} />
                <div>
                    <h3 className="font-semibold text-lg text-white">System Health</h3>
                    <p className="text-sm text-blue-300">
                        {isIngesting ? "Pipeline Active - Processing Real-time" : "Pipeline Idle"}
                    </p>
                </div>
            </div>
            <div className="flex items-center space-x-2">
                <span className={`h-3 w-3 rounded-full ${isIngesting ? 'bg-emerald-500 animate-pulse' : 'bg-blue-500'}`}></span>
                <span className="text-sm uppercase tracking-wider font-medium text-blue-300">
                    {isIngesting ? "Operational" : "Standby"}
                </span>
            </div>
        </div>
    );
};

export default PipelineHealth;
