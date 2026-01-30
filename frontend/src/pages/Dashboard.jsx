import React, { useState, useEffect } from 'react';
import StatsGrid from '../components/StatsGrid';
import PipelineHealth from '../components/PipelineHealth';
import RecentEmails from '../components/RecentEmails';
import SimulationBox from '../components/SimulationBox';
import ExportButton from '../components/ExportButton';
import GmailConfig from '../components/GmailConfig';

const Dashboard = () => {
    const [stats, setStats] = useState({});
    const [emails, setEmails] = useState([]);

    // Pagination State
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const pageSize = 20;

    const [isIngesting, setIsIngesting] = useState(false);

    const fetchData = async () => {
        try {
            const statsRes = await fetch('http://localhost:8001/api/stats');
            const statsData = await statsRes.json();
            setStats(statsData);

            // Fetch with pagination
            const emailsRes = await fetch(`http://localhost:8001/api/emails?page=${currentPage}&limit=${pageSize}`);
            const emailsResponse = await emailsRes.json();

            setEmails(emailsResponse.items || []);
            setTotalPages(Math.ceil((emailsResponse.total || 0) / pageSize));

            // Pipeline is active if there are pending OR processing emails
            setIsIngesting(statsData.pending > 0 || statsData.processing > 0);
        } catch (e) {
            console.error("Failed to fetch data:", e);
        }
    };

    const handleInject = async (data) => {
        try {
            await fetch('http://localhost:8001/api/ingest', {
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

            await fetch('http://localhost:8001/api/ingest/bulk', {
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
    }, [currentPage]); // Re-fetch when page changes

    return (
        <div className="p-8 max-w-[1600px] mx-auto">
            <div className="flex justify-between items-center mb-8">
                <div className="flex items-center gap-4">
                    <img 
                        src="/lic-logo-bg.png" 
                        alt="LIC Logo" 
                        className="h-20 w-20 object-cover flex-shrink-0"
                        style={{
                            filter: 'brightness(0.9) contrast(1.2) invert(1) hue-rotate(180deg) saturate(1.5)',
                            mixBlendMode: 'lighten'
                        }}
                    />
                    <div>
                        <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-pink-500">
                            LIC Email Intelligence Platform
                        </h1>
                        <p className="text-gray-400 mt-1">Real-time Claims & Policy Analysis Agent</p>
                    </div>
                </div>
                <ExportButton />
            </div>

            <PipelineHealth isIngesting={isIngesting} />
            <StatsGrid stats={stats} />

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
                <div className="lg:col-span-3">
                    <RecentEmails
                        emails={emails}
                        currentPage={currentPage}
                        totalPages={totalPages}
                        onPageChange={setCurrentPage}
                    />
                </div>
                <div className="lg:col-span-1 space-y-6">
                    <GmailConfig onSync={fetchData} />
                    <SimulationBox onInject={handleInject} onBulkInject={handleBulkInject} />
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
