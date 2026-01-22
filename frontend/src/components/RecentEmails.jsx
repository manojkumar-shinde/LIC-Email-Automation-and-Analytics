import React from 'react';
import { FileText, User, Tag, Lightbulb } from 'lucide-react';

const RecentEmails = ({ emails, currentPage, totalPages, onPageChange }) => {
    return (
        <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
            <div className="p-6 border-b border-gray-700">
                <h2 className="text-xl font-bold flex items-center">
                    <FileText className="w-5 h-5 mr-2 text-indigo-400" />
                    Live Feed
                </h2>
            </div>
            <div className="overflow-x-auto">
                <table className="w-full text-left">
                    <thead className="bg-gray-900 text-gray-400 text-xs uppercase">
                        <tr>
                            <th className="p-4">Sender</th>
                            <th className="p-4">Subject</th>
                            <th className="p-4">Intent</th>
                            <th className="p-4">Sentiment</th>
                            <th className="p-4">Confidence</th>
                            <th className="p-4">Summary</th>
                            <th className="p-4">Status</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700">
                        {emails.map((email) => (
                            <tr key={email.id} className="hover:bg-gray-750 transition-colors">
                                <td className="p-4 flex items-center space-x-2">
                                    <User className="w-4 h-4 text-gray-500" />
                                    <span className="truncate max-w-[150px]">{email.sender}</span>
                                </td>
                                <td className="p-4 max-w-[200px] truncate" title={email.subject}>
                                    {email.subject}
                                </td>
                                <td className="p-4">
                                    <span className="px-2 py-1 rounded-md text-xs font-medium bg-indigo-900 text-indigo-300 border border-indigo-700">
                                        {email.analysis?.intent || '...'}
                                    </span>
                                </td>
                                <td className="p-4">
                                    <span className={`px-2 py-1 rounded-md text-xs font-medium border ${email.analysis?.sentiment === 'NEGATIVE' ? 'bg-red-900 text-red-300 border-red-700' :
                                        email.analysis?.sentiment === 'POSITIVE' ? 'bg-green-900 text-green-300 border-green-700' :
                                            'bg-gray-700 text-gray-300 border-gray-600'
                                        }`}>
                                        {email.analysis?.sentiment || '...'}
                                    </span>
                                </td>
                                <td className="p-4">
                                    <span className={`px-2 py-1 rounded-md text-xs font-medium border ${email.analysis?.confidence === 'Low' ? 'bg-red-900 text-red-300 border-red-700' :
                                        email.analysis?.confidence === 'High' ? 'bg-green-900 text-green-300 border-green-700' :
                                            'bg-gray-700 text-gray-300 border-gray-600'
                                        }`}>
                                        {email.analysis?.confidence || '...'}
                                    </span>
                                </td>
                                <td className="p-4 max-w-[300px]">
                                    <div className="flex items-start space-x-2">
                                        <Lightbulb className="w-4 h-4 text-yellow-500 mt-1 flex-shrink-0" />
                                        <span className="text-sm text-gray-300">
                                            {/* We mapped summary to suggested_action column in backend */}
                                            {email.analysis?.summary || email.suggested_action || 'Pending Analysis...'}
                                        </span>
                                    </div>
                                </td>
                                <td className="p-4">
                                    <span className={`text-xs font-bold ${email.status === 'COMPLETED' ? 'text-green-400' : 'text-yellow-400'
                                        }`}>
                                        {email.status}
                                    </span>
                                </td>
                            </tr>
                        ))}
                        {emails.length === 0 && (
                            <tr>
                                <td colSpan="6" className="p-8 text-center text-gray-500">
                                    No emails found. Waiting for ingestion...
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            {/* Pagination Footer */}
            <div className="p-4 border-t border-gray-700 flex justify-between items-center bg-gray-900/50">
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
