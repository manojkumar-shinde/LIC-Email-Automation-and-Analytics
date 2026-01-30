import React from 'react';
import { FileText } from 'lucide-react';
import EmailTile from './EmailTile';

const RecentEmails = ({ emails, currentPage, totalPages, onPageChange }) => {
    return (
        <div className="tile-transparent rounded-xl overflow-hidden">
            <div className="p-6 border-b border-gray-600 border-opacity-30">
                <h2 className="text-xl font-bold flex items-center">
                    <FileText className="w-5 h-5 mr-2 text-indigo-400" />
                    Live Feed
                </h2>
            </div>

            {/* Tile Grid Layout */}
            <div className="p-6">
                {emails.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {emails.map((email) => (
                            <EmailTile key={email.id} email={email} />
                        ))}
                    </div>
                ) : (
                    <div className="p-8 text-center text-gray-500">
                        No emails found. Waiting for ingestion...
                    </div>
                )}
            </div>

            {/* Pagination Footer - Unchanged */}
            <div className="p-4 border-t border-gray-600 border-opacity-30 flex justify-between items-center">
                <button
                    onClick={() => onPageChange(currentPage - 1)}
                    disabled={currentPage === 1}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${currentPage === 1
                            ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
                            : 'bg-gray-700 text-gray-200 hover:bg-gray-600'
                        }`}
                >
                    Previous
                </button>

                <span className="text-gray-400 text-sm">
                    Page <span className="text-white font-bold">{currentPage}</span> of {totalPages}
                </span>

                <button
                    onClick={() => onPageChange(currentPage + 1)}
                    disabled={currentPage >= totalPages}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${currentPage >= totalPages
                            ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
                            : 'bg-gray-700 text-gray-200 hover:bg-gray-600'
                        }`}
                >
                    Next
                </button>
            </div>
        </div>
    );
};

export default RecentEmails;
