import React, { useState, useEffect } from 'react';
import StatsGrid from '../components/StatsGrid';
import PipelineHealth from '../components/PipelineHealth';
import RecentEmails from '../components/RecentEmails';
import SimulationBox from '../components/SimulationBox';
import ExportButton from '../components/ExportButton';

const Dashboard = () => {
    const [stats, setStats] = useState({});
    const [emails, setEmails] = useState([]);
    const [isIngesting, setIsIngesting] = useState(false);

    const fetchData = async () => {
        try {
            const statsRes = await fetch('http://localhost:8000/api/stats');
            const statsData = await statsRes.json();
            setStats(statsData);

            const emailsRes = await fetch('http://localhost:8000/api/emails');
            const emailsData = await emailsRes.json();
            setEmails(emailsData);

            // Simple heuristic for "Ingesting": if pending > 0
            setIsIngesting(statsData.pending > 0);
        } catch (e) {
            console.error("Failed to fetch data:", e);
        }
    };

    const handleInject = async (data) => {
        try {
            await fetch('http://localhost:8000/api/ingest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            fetchData(); // Immediate refresh
        } catch (e) {
            console.error("Injection failed:", e);
        }
    };

    const handleBulkInject = async (file) => {
        try {
            const formData = new FormData();
            formData.append('file', file);

            await fetch('http://localhost:8000/api/ingest/bulk', {
                method: 'POST',
                body: formData
            });
            fetchData(); // Immediate refresh
        } catch (e) {
            console.error("Bulk injection failed:", e);
        }
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 2000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="p-8 max-w-[1600px] mx-auto">
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-pink-500">
                        LIC Email Intelligence Platform
                    </h1>
                    <p className="text-gray-400 mt-1">Real-time Claims & Policy Analysis Agent</p>
                </div>
                <ExportButton />
            </div>

            <PipelineHealth isIngesting={isIngesting} />
            <StatsGrid stats={stats} />

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
                <div className="lg:col-span-3">
                    <RecentEmails emails={emails} />
                </div>
                <div className="lg:col-span-1">
                    <SimulationBox onInject={handleInject} onBulkInject={handleBulkInject} />
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
