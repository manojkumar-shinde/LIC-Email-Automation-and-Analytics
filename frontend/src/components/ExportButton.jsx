import React from 'react';
import { Download } from 'lucide-react';

const ExportButton = () => {
    const handleDownload = () => {
        window.open('/api/export', '_blank');
    };

    return (
        <button
            onClick={handleDownload}
            className="flex items-center space-x-2 bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg transition-colors border border-gray-600"
        >
            <Download className="w-4 h-4" />
            <span>Export CSV</span>
        </button>
    );
};

export default ExportButton;
