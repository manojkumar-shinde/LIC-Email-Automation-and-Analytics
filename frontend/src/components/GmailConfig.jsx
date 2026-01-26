import React, { useState, useEffect } from 'react';
import { Mail, Plus, Trash2, RefreshCw, CheckCircle, AlertCircle, Loader } from 'lucide-react';

const GmailConfig = ({ onSync }) => {
    const [accounts, setAccounts] = useState([]);
    const [stats, setStats] = useState({});
    const [isLoading, setIsLoading] = useState(false);
    const [isSyncing, setIsSyncing] = useState(false);
    const [showForm, setShowForm] = useState(false);
    const [error, setError] = useState('');
    const [successMsg, setSuccessMsg] = useState('');

    // Form state
    const [formData, setFormData] = useState({
        gmail_email: '',
        auth_method: 'token',
        api_key: ''
    });

    // Fetch Gmail accounts and stats
    const fetchGmailAccounts = async () => {
        setIsLoading(true);
        try {
            const response = await fetch('http://localhost:8001/api/gmail/accounts');
            const data = await response.json();
            
            if (data.status === 'success') {
                setAccounts(data.data.accounts || []);
                setStats(data.data.stats || {});
            } else {
                setError('Failed to fetch Gmail accounts');
            }
        } catch (err) {
            setError('Error connecting to server: ' + err.message);
        } finally {
            setIsLoading(false);
        }
    };

    // Connect Gmail account
    const handleConnect = async (e) => {
        e.preventDefault();
        setError('');
        setSuccessMsg('');

        if (!formData.gmail_email || !formData.api_key) {
            setError('Please fill in all fields');
            return;
        }

        setIsLoading(true);
        try {
            const response = await fetch('http://localhost:8001/api/gmail/connect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            const data = await response.json();

            if (data.status === 'success') {
                setSuccessMsg(`Successfully connected: ${formData.gmail_email}`);
                setFormData({ gmail_email: '', auth_method: 'token', api_key: '' });
                setShowForm(false);
                fetchGmailAccounts();
                
                // Clear success message after 3 seconds
                setTimeout(() => setSuccessMsg(''), 3000);
            } else {
                setError(data.message || 'Failed to connect Gmail account');
            }
        } catch (err) {
            setError('Error: ' + err.message);
        } finally {
            setIsLoading(false);
        }
    };

    // Trigger sync
    const handleSync = async (gmail_email = null) => {
        setIsSyncing(true);
        try {
            const url = gmail_email
                ? `http://localhost:8001/api/gmail/sync?gmail_email=${encodeURIComponent(gmail_email)}`
                : 'http://localhost:8001/api/gmail/sync';

            const response = await fetch(url, { method: 'POST' });
            const data = await response.json();

            if (data.status === 'syncing') {
                setSuccessMsg(`Sync started for ${gmail_email || 'all accounts'}`);
                fetchGmailAccounts();
                if (onSync) onSync();
                
                // Clear success message after 3 seconds
                setTimeout(() => setSuccessMsg(''), 3000);
            } else {
                setError('Failed to start sync');
            }
        } catch (err) {
            setError('Error: ' + err.message);
        } finally {
            setIsSyncing(false);
        }
    };

    // Toggle sync for account
    const handleToggle = async (gmail_email, enabled) => {
        try {
            const response = await fetch(
                `http://localhost:8001/api/gmail/toggle?gmail_email=${encodeURIComponent(gmail_email)}&enabled=${!enabled}`,
                { method: 'POST' }
            );

            const data = await response.json();
            if (data.status === 'success') {
                fetchGmailAccounts();
            } else {
                setError('Failed to toggle sync');
            }
        } catch (err) {
            setError('Error: ' + err.message);
        }
    };

    // Disconnect account
    const handleDisconnect = async (gmail_email) => {
        if (!window.confirm(`Are you sure you want to disconnect ${gmail_email}?`)) {
            return;
        }

        try {
            const response = await fetch(
                `http://localhost:8001/api/gmail/disconnect?gmail_email=${encodeURIComponent(gmail_email)}`,
                { method: 'DELETE' }
            );

            const data = await response.json();
            if (data.status === 'success') {
                setSuccessMsg(`Disconnected: ${gmail_email}`);
                fetchGmailAccounts();
                setTimeout(() => setSuccessMsg(''), 3000);
            } else {
                setError('Failed to disconnect');
            }
        } catch (err) {
            setError('Error: ' + err.message);
        }
    };

    // Load accounts on mount
    useEffect(() => {
        fetchGmailAccounts();
        // Refresh every 30 seconds
        const interval = setInterval(fetchGmailAccounts, 30000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 shadow-lg">
            <div className="flex justify-between items-center mb-6">
                <h3 className="text-lg font-bold flex items-center">
                    <Mail className="w-5 h-5 mr-2 text-blue-500" />
                    Gmail Integration
                </h3>
                <button
                    onClick={() => setShowForm(!showForm)}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition"
                    disabled={isLoading}
                >
                    <Plus className="w-4 h-4" />
                    Add Account
                </button>
            </div>

            {/* Error Message */}
            {error && (
                <div className="mb-4 p-3 bg-red-900 bg-opacity-30 border border-red-500 rounded-lg flex items-start gap-2">
                    <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                    <div>
                        <p className="text-red-200 text-sm">{error}</p>
                    </div>
                </div>
            )}

            {/* Success Message */}
            {successMsg && (
                <div className="mb-4 p-3 bg-green-900 bg-opacity-30 border border-green-500 rounded-lg flex items-start gap-2">
                    <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                    <p className="text-green-200 text-sm">{successMsg}</p>
                </div>
            )}

            {/* Connect Form */}
            {showForm && (
                <div className="mb-6 p-4 bg-gray-700 rounded-lg border border-gray-600">
                    <h4 className="font-semibold mb-4">Connect Gmail Account</h4>
                    <form onSubmit={handleConnect} className="space-y-4">
                        <div>
                            <label className="block text-sm text-gray-300 mb-1">Gmail Email</label>
                            <input
                                type="email"
                                placeholder="your.email@gmail.com"
                                value={formData.gmail_email}
                                onChange={(e) => setFormData({ ...formData, gmail_email: e.target.value })}
                                className="w-full px-3 py-2 bg-gray-600 border border-gray-500 rounded text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
                                required
                            />
                        </div>

                        <div>
                            <label className="block text-sm text-gray-300 mb-1">Auth Method</label>
                            <select
                                value={formData.auth_method}
                                onChange={(e) => setFormData({ ...formData, auth_method: e.target.value })}
                                className="w-full px-3 py-2 bg-gray-600 border border-gray-500 rounded text-white focus:outline-none focus:border-blue-500"
                            >
                                <option value="token">Access Token</option>
                                <option value="service_account">Service Account JSON</option>
                                <option value="oauth">OAuth (Browser Login)</option>
                            </select>
                        </div>

                        <div>
                            <label className="block text-sm text-gray-300 mb-1">
                                {formData.auth_method === 'service_account' ? 'Service Account JSON' : 'API Key / Token'}
                            </label>
                            <textarea
                                placeholder={formData.auth_method === 'token' 
                                    ? 'Paste your OAuth access token here...'
                                    : 'Paste your service account JSON here...'}
                                value={formData.api_key}
                                onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                                className="w-full px-3 py-2 bg-gray-600 border border-gray-500 rounded text-white placeholder-gray-400 focus:outline-none focus:border-blue-500 font-mono text-xs"
                                rows="4"
                                required
                            />
                        </div>

                        <div className="flex gap-2">
                            <button
                                type="submit"
                                disabled={isLoading}
                                className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white rounded-lg transition flex items-center justify-center gap-2"
                            >
                                {isLoading ? <Loader className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                                {isLoading ? 'Connecting...' : 'Connect'}
                            </button>
                            <button
                                type="button"
                                onClick={() => {
                                    setShowForm(false);
                                    setFormData({ gmail_email: '', auth_method: 'token', api_key: '' });
                                    setError('');
                                }}
                                className="flex-1 px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition"
                            >
                                Cancel
                            </button>
                        </div>
                    </form>
                </div>
            )}

            {/* Stats */}
            {accounts.length > 0 && (
                <div className="mb-6 grid grid-cols-2 gap-4">
                    <div className="bg-gray-700 p-3 rounded-lg">
                        <p className="text-xs text-gray-400">Total Accounts</p>
                        <p className="text-2xl font-bold">{stats.total_accounts || 0}</p>
                    </div>
                    <div className="bg-gray-700 p-3 rounded-lg">
                        <p className="text-xs text-gray-400">Emails Synced</p>
                        <p className="text-2xl font-bold">{stats.total_emails_synced || 0}</p>
                    </div>
                </div>
            )}

            {/* Accounts List */}
            {isLoading && !accounts.length ? (
                <div className="flex justify-center py-8">
                    <Loader className="w-6 h-6 animate-spin text-blue-500" />
                </div>
            ) : accounts.length > 0 ? (
                <div className="space-y-3">
                    <div className="flex justify-between items-center mb-4">
                        <h4 className="font-semibold text-sm">Connected Accounts</h4>
                        <button
                            onClick={() => handleSync()}
                            disabled={isSyncing}
                            className="flex items-center gap-1 px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded transition"
                        >
                            {isSyncing ? (
                                <>
                                    <Loader className="w-3 h-3 animate-spin" />
                                    Syncing...
                                </>
                            ) : (
                                <>
                                    <RefreshCw className="w-3 h-3" />
                                    Sync All
                                </>
                            )}
                        </button>
                    </div>

                    {accounts.map((account) => (
                        <div key={account.gmail_email} className="bg-gray-700 p-4 rounded-lg border border-gray-600 space-y-2">
                            <div className="flex justify-between items-start">
                                <div className="flex-1">
                                    <p className="font-medium text-white">{account.gmail_email}</p>
                                    <p className="text-xs text-gray-400">{account.auth_method}</p>
                                </div>
                                <div className="flex items-center gap-1">
                                    {account.sync_enabled ? (
                                        <span className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-green-900 bg-opacity-50 text-green-300 rounded">
                                            <CheckCircle className="w-3 h-3" />
                                            Enabled
                                        </span>
                                    ) : (
                                        <span className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-gray-600 text-gray-300 rounded">
                                            Disabled
                                        </span>
                                    )}
                                </div>
                            </div>

                            <div className="text-xs text-gray-400">
                                {account.last_sync_time ? (
                                    <>
                                        <p>Last sync: {new Date(account.last_sync_time).toLocaleString()}</p>
                                        <p className="mt-1">Emails synced: {account.total_synced}</p>
                                        {account.last_sync_status === 'success' ? (
                                            <p className="text-green-400 mt-1">✓ Last sync successful</p>
                                        ) : account.last_sync_status === 'failed' ? (
                                            <p className="text-red-400 mt-1">✗ Last sync failed {account.last_sync_error ? `: ${account.last_sync_error}` : ''}</p>
                                        ) : (
                                            <p className="text-yellow-400 mt-1">◐ Pending</p>
                                        )}
                                    </>
                                ) : (
                                    <p className="text-yellow-400">Not synced yet</p>
                                )}
                            </div>

                            <div className="flex gap-2 pt-2">
                                <button
                                    onClick={() => handleSync(account.gmail_email)}
                                    disabled={isSyncing}
                                    className="flex-1 flex items-center justify-center gap-1 px-3 py-1 text-xs bg-blue-700 hover:bg-blue-800 disabled:bg-gray-600 text-white rounded transition"
                                >
                                    {isSyncing ? (
                                        <Loader className="w-3 h-3 animate-spin" />
                                    ) : (
                                        <RefreshCw className="w-3 h-3" />
                                    )}
                                    Sync
                                </button>

                                <button
                                    onClick={() => handleToggle(account.gmail_email, account.sync_enabled)}
                                    className={`flex-1 px-3 py-1 text-xs rounded transition ${
                                        account.sync_enabled
                                            ? 'bg-gray-600 hover:bg-gray-700 text-gray-300'
                                            : 'bg-green-700 hover:bg-green-800 text-white'
                                    }`}
                                >
                                    {account.sync_enabled ? 'Disable' : 'Enable'}
                                </button>

                                <button
                                    onClick={() => handleDisconnect(account.gmail_email)}
                                    className="flex items-center justify-center gap-1 px-3 py-1 text-xs bg-red-700 hover:bg-red-800 text-white rounded transition"
                                >
                                    <Trash2 className="w-3 h-3" />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            ) : (
                <div className="text-center py-8">
                    <Mail className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                    <p className="text-gray-400">No Gmail accounts connected</p>
                    <p className="text-xs text-gray-500 mt-1">Add an account to start syncing emails</p>
                </div>
            )}
        </div>
    );
};

export default GmailConfig;
