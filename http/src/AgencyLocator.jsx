import React, { useState } from 'react';
import { Input } from './components/ui/input';
import { Button } from './components/ui/button';
import { Card, CardContent } from './components/ui/card';

export default function AgencyLocator() {
  const [zip, setZip] = useState('');
  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const search = async () => {
    setLoading(true);
    setError(null);
    setResults([]);
    try {
      const params = zip
          ? `zipcode=${zip}`
          : city && state
          ? `city=${encodeURIComponent(city)}&state=${state}`
          : '';
      const res = await fetch(`/agencies/nearby?${params}`);
      const data = await res.json();
      if (data.error) {
        setError(data.error);
      } else {
        setResults(data);
      }
    } catch (e) {
      setError('Failed to fetch data.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-950 text-white">
      <header className="border-b border-gray-800 shadow-md sticky top-0 z-50 bg-gray-900">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-indigo-400 text-xl font-bold">ABOLISH ICE NOW</span>
          </div>
          <nav className="flex items-center gap-4 text-sm">
            <button
              onClick={() => navigator.share && navigator.share({ title: '287(g) Agency Lookup', url: window.location.href })}
              className="px-3 py-1 bg-indigo-600 hover:bg-indigo-700 rounded text-white text-sm transition"
            >
              Share
            </button>
          </nav>
        </div>
      </header>
      <main id="search" className="p-6 max-w-3xl mx-auto bg-gray-900 min-h-screen text-white">
        <h1 className="text-3xl font-bold mb-6 text-center text-indigo-300">Is my police department collaborating with ICE?</h1>
        <div className="grid gap-4 sm:grid-cols-2 mb-4">
          <Input placeholder="ZIP code" value={zip} onChange={e => setZip(e.target.value)} className="bg-gray-800 text-white border-gray-600 focus:border-indigo-500 focus:ring-indigo-500" />
          <div className="grid grid-cols-2 gap-2">
            <Input placeholder="City" value={city} onChange={e => setCity(e.target.value)} className="bg-gray-800 text-white border-gray-600 focus:border-indigo-500 focus:ring-indigo-500" />
            <Input placeholder="State (e.g. NY)" value={state} onChange={e => setState(e.target.value)} className="bg-gray-800 text-white border-gray-600 focus:border-indigo-500 focus:ring-indigo-500" />
          </div>
        </div>
        <Button onClick={search} disabled={loading} className="w-full bg-indigo-600 hover:bg-indigo-700 text-white">
          {loading ? 'Searching...' : 'Search'}
        </Button>
        {error && <p className="text-indigo-400 mt-4 text-center font-medium">{error}</p>}
        <div className="mt-6 grid gap-4">
          {results.map((agency, idx) => {
            const statusClass = agency['SUPPORT TYPE'] === 'Pending'
              ? 'bg-yellow-500 text-black'
              : 'bg-green-500 text-white';
            const statusText = agency['SUPPORT TYPE'] === 'Pending' ? 'Pending' : 'Participating';

            return (
              <Card key={idx} className="bg-gray-800 border-gray-700 text-white shadow-lg hover:shadow-xl transition">
                <CardContent className="p-4 rounded-xl">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-lg font-semibold text-indigo-300">{agency['LAW ENFORCEMENT AGENCY']}</p>
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${statusClass}`}>
                      {statusText}
                    </span>
                  </div>
                  <p className="text-sm text-gray-400">{agency.STATE}</p>
                  <p className="text-sm text-indigo-400">Support Type: {agency['SUPPORT TYPE']}</p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </main>
    </div>
  );
}