import React, { useState } from 'react';
import { Send } from 'lucide-react';

const SimulationBox = ({ onInject, onBulkInject }) => {
    const [mode, setMode] = useState('single'); // 'single' or 'bulk'
    const [subject, setSubject] = useState('');
    const [body, setBody] = useState('');
    const [file, setFile] = useState(null);

    const handleSubmit = (e) => {
        e.preventDefault();
        if (mode === 'single') {
            if (!subject || !body) return;
            onInject({ sender: 'customer@example.com', subject, body });
            setSubject('');
            setBody('');
        } else {
            if (!file) return;
            onBulkInject(file);
            setFile(null);
            // Reset file input value manually if needed, but react state handle is enough usually
            document.getElementById('bulk-file-input').value = "";
        }
    };

    return (
        <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 h-full flex flex-col">
            <h3 className="text-lg font-bold mb-4 flex items-center">
                <Send className="w-5 h-5 mr-2 text-pink-500" />
                Manual Simulator
            </h3>

            <div className="flex space-x-2 mb-4">
                <button
                    onClick={() => setMode('single')}
                    className={`flex-1 py-1 text-sm rounded ${mode === 'single' ? 'bg-pink-600 text-white' : 'bg-gray-700 text-gray-400 hover:bg-gray-600'}`}
                >
                    Single
                </button>
                <button
                    onClick={() => setMode('bulk')}
                    className={`flex-1 py-1 text-sm rounded ${mode === 'bulk' ? 'bg-pink-600 text-white' : 'bg-gray-700 text-gray-400 hover:bg-gray-600'}`}
                >
                    Bulk (File)
                </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4 flex-1 flex flex-col">
                {mode === 'single' ? (
                    <>
                        <div>
                            <label className="block text-sm text-gray-400 mb-1">Subject</label>
                            <input
                                type="text"
                                value={subject}
                                onChange={(e) => setSubject(e.target.value)}
                                className="w-full bg-gray-900 border border-gray-600 rounded p-2 text-sm focus:border-pink-500 outline-none"
                                placeholder="e.g. Surrender Request Policy #123"
                            />
                        </div>
                        <div>
                            <label className="block text-sm text-gray-400 mb-1">Body</label>
                            <textarea
                                value={body}
                                onChange={(e) => setBody(e.target.value)}
                                className="w-full bg-gray-900 border border-gray-600 rounded p-2 text-sm h-24 focus:border-pink-500 outline-none resize-none"
                                placeholder="Type email body..."
                            />
                        </div>
                    </>
                ) : (
                    <div className="flex-1 flex flex-col justify-center items-center border-2 border-dashed border-gray-700 rounded-lg p-4 hover:border-gray-500 transition-colors">
                        <input
                            id="bulk-file-input"
                            type="file"
                            accept=".json,.csv"
                            onChange={(e) => setFile(e.target.files[0])}
                            className="hidden"
                        />
                        <label htmlFor="bulk-file-input" className="cursor-pointer text-center">
                            <div className="text-pink-500 mb-2 font-bold">
                                {file ? file.name : "Select File"}
                            </div>
                            <div className="text-gray-400 text-xs">
                                {file ? `${(file.size / 1024).toFixed(1)} KB` : "Drop .json or .csv here"}
                            </div>
                        </label>
                    </div>
                )}

                <button
                    type="submit"
                    className="w-full bg-pink-600 hover:bg-pink-700 text-white font-bold py-2 px-4 rounded transition-colors flex justify-center items-center mt-auto"
                >
                    {mode === 'single' ? 'Inject Traffic' : 'Upload Bulk Data'}
                </button>
            </form>
        </div>
    );
};

export default SimulationBox;
