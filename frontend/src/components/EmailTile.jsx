import React from 'react';
import { User, Tag, Lightbulb, Mail } from 'lucide-react';

/**
 * EmailTile Component
 * 
 * Displays individual email as a card/tile with priority-based color coding.
 * 
 * Priority Color Scheme:
 * - HIGH: Red accent border + subtle red background tint
 * - MEDIUM: Gray accent border + neutral background
 * - LOW: Green accent border + subtle green background tint
 */

const getPriorityStyles = (priority) => {
    switch (priority?.toUpperCase()) {
        case 'HIGH':
            return {
                container: 'bg-red-500/5 border-l-red-500 hover:bg-red-500/10',
                badge: 'bg-red-900 text-red-300 border-red-700',
                icon: 'text-red-400'
            };
        case 'LOW':
            return {
                container: 'bg-green-500/5 border-l-green-500 hover:bg-green-500/10',
                badge: 'bg-green-900 text-green-300 border-green-700',
                icon: 'text-green-400'
            };
        default: // MEDIUM or undefined
            return {
                container: 'bg-gray-800 border-l-gray-600 hover:bg-gray-750',
                badge: 'bg-gray-700 text-gray-300 border-gray-600',
                icon: 'text-gray-400'
            };
    }
};

const getSentimentStyles = (sentiment) => {
    switch (sentiment?.toUpperCase()) {
        case 'NEGATIVE':
            return 'bg-red-900 text-red-300 border-red-700';
        case 'POSITIVE':
            return 'bg-green-900 text-green-300 border-green-700';
        default:
            return 'bg-gray-700 text-gray-300 border-gray-600';
    }
};

const EmailTile = ({ email }) => {
    const priority = email.analysis?.priority || 'MEDIUM';
    const styles = getPriorityStyles(priority);

    return (
        <div
            className={`
                ${styles.container}
                border-l-4 border-t border-r border-b border-gray-700
                rounded-lg p-4 
                transition-all duration-200 
                cursor-pointer
                shadow-lg hover:shadow-xl
            `}
        >
            {/* Priority Badge */}
            <div className="flex justify-between items-start mb-3">
                <span className={`
                    ${styles.badge}
                    px-2 py-1 rounded-md text-xs font-bold uppercase border
                `}>
                    {priority}
                </span>

                {/* Status Indicator */}
                <span className={`
                    text-xs font-bold
                    ${email.status === 'COMPLETED' ? 'text-green-400' :
                        email.status === 'PROCESSING' ? 'text-yellow-400' :
                            'text-gray-400'}
                `}>
                    {email.status}
                </span>
            </div>

            {/* Sender */}
            <div className="flex items-center space-x-2 mb-2">
                <User className={`w-4 h-4 ${styles.icon}`} />
                <span className="text-sm text-gray-300 truncate">
                    {email.sender}
                </span>
            </div>

            {/* Subject */}
            <div className="flex items-start space-x-2 mb-3">
                <Mail className={`w-4 h-4 ${styles.icon} mt-0.5 flex-shrink-0`} />
                <h3 className="text-sm font-semibold text-white line-clamp-2">
                    {email.subject}
                </h3>
            </div>

            {/* Summary */}
            <div className="flex items-start space-x-2 mb-3 min-h-[60px]">
                <Lightbulb className="w-4 h-4 text-yellow-500 mt-1 flex-shrink-0" />
                <p className="text-xs text-gray-400 line-clamp-3">
                    {email.analysis?.summary || email.suggested_action || 'Pending Analysis...'}
                </p>
            </div>

            {/* Generated Reply Section */}
            {email.generated_reply && (
                <div className="mb-3 pt-3 border-t border-gray-700">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-semibold text-gray-400 uppercase">
                            📧 Generated Reply Draft
                        </span>
                        {email.generated_reply === 'NO_REPLY' && (
                            <span className="px-2 py-1 rounded-md text-xs font-bold bg-yellow-900 text-yellow-300 border border-yellow-700">
                                ⚠️ SAFETY BLOCKED
                            </span>
                        )}
                    </div>
                    {email.generated_reply === 'NO_REPLY' ? (
                        <div className="bg-yellow-900/20 border border-yellow-700/50 rounded-md p-3">
                            <p className="text-xs text-yellow-300 font-medium">
                                ⚠️ No reply generated - requires human review
                            </p>
                            <p className="text-xs text-yellow-400/70 mt-1">
                                This email contains sensitive keywords, high priority, or claims-related content that requires manual handling.
                            </p>
                        </div>
                    ) : (
                        <div className="bg-blue-900/20 border border-blue-700/50 rounded-md p-3">
                            <p className="text-xs text-gray-300 leading-relaxed whitespace-pre-line">
                                {email.generated_reply}
                            </p>
                            <p className="text-xs text-blue-400/70 mt-2 italic">
                                ⚠️ Draft only - requires human review before sending
                            </p>
                        </div>
                    )}
                </div>
            )}

            {/* Metadata: Intent, Sentiment */}
            <div className="flex flex-wrap gap-2 pt-3 border-t border-gray-700">
                {/* Intent Badge */}
                <span className="px-2 py-1 rounded-md text-xs font-medium bg-indigo-900 text-indigo-300 border border-indigo-700 flex items-center">
                    <Tag className="w-3 h-3 mr-1" />
                    {email.analysis?.intent || 'N/A'}
                </span>

                {/* Sentiment Badge */}
                <span className={`
                    px-2 py-1 rounded-md text-xs font-medium border
                    ${getSentimentStyles(email.analysis?.sentiment)}
                `}>
                    {email.analysis?.sentiment || 'N/A'}
                </span>

                {/* Confidence (optional) */}
                {email.analysis?.confidence && (
                    <span className={`
                        px-2 py-1 rounded-md text-xs font-medium border
                        ${email.analysis.confidence === 'High' ? 'bg-green-900 text-green-300 border-green-700' :
                            email.analysis.confidence === 'Low' ? 'bg-red-900 text-red-300 border-red-700' :
                                'bg-gray-700 text-gray-300 border-gray-600'}
                    `}>
                        {email.analysis.confidence}
                    </span>
                )}
            </div>
        </div>
    );
};

export default EmailTile;
