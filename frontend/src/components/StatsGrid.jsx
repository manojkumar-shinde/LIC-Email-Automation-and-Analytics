import React from 'react';
import { Mail, CheckCircle, AlertTriangle, Clock } from 'lucide-react';

const StatCard = ({ icon: Icon, label, value, color }) => (
    <div className="tile-transparent p-6 rounded-xl shadow-lg flex items-center space-x-4 group">
        <div className={`p-3 rounded-full bg-opacity-20 ${color} group-hover:bg-opacity-30 transition-all`}>
            <Icon className={`w-8 h-8 ${color.replace('bg-', 'text-')}`} />
        </div>
        <div>
            <p className="text-blue-300 text-sm font-medium">{label}</p>
            <p className="text-3xl font-bold text-white">{value}</p>
        </div>
    </div>
);

const StatsGrid = ({ stats }) => {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <StatCard
                icon={Mail}
                label="Pending Emails"
                value={stats.pending || 0}
                color="bg-blue-500 text-blue-400"
            />
            <StatCard
                icon={Clock}
                label="Avg Processing (s)"
                value={stats.avg_latency || 0}
                color="bg-amber-500 text-amber-400"
            />
            <StatCard
                icon={CheckCircle}
                label="Completed"
                value={stats.completed || 0}
                color="bg-emerald-500 text-emerald-400"
            />
            <StatCard
                icon={AlertTriangle}
                label="Failed"
                value={stats.failed || 0}
                color="bg-rose-500 text-rose-400"
            />
        </div>
    );
};

export default StatsGrid;
