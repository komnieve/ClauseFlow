import { useState, useEffect } from 'react';
import { getCustomers, createCustomer } from '../api/client';

/**
 * Customer dropdown with inline "Create new" option
 */
export default function CustomerSelector({ selectedCustomerId, onSelect, className = '' }) {
  const [customers, setCustomers] = useState([]);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState('');
  const [error, setError] = useState(null);

  useEffect(() => {
    loadCustomers();
  }, []);

  const loadCustomers = async () => {
    try {
      const data = await getCustomers();
      setCustomers(data);
    } catch (err) {
      console.error('Failed to load customers:', err);
    }
  };

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setError(null);
    try {
      const customer = await createCustomer(newName.trim());
      setCustomers(prev => [...prev, customer].sort((a, b) => a.name.localeCompare(b.name)));
      onSelect(customer.id);
      setCreating(false);
      setNewName('');
    } catch (err) {
      setError(err.message);
    }
  };

  if (creating) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <input
          type="text"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
          placeholder="Customer name..."
          className="px-3 py-1.5 border rounded text-sm flex-1"
          autoFocus
        />
        <button
          onClick={handleCreate}
          className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
        >
          Add
        </button>
        <button
          onClick={() => { setCreating(false); setNewName(''); setError(null); }}
          className="px-3 py-1.5 text-gray-600 text-sm hover:text-gray-800"
        >
          Cancel
        </button>
        {error && <span className="text-red-500 text-xs">{error}</span>}
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <select
        value={selectedCustomerId || ''}
        onChange={(e) => onSelect(e.target.value ? parseInt(e.target.value) : null)}
        className="px-3 py-1.5 border rounded text-sm"
      >
        <option value="">No customer</option>
        {customers.map(c => (
          <option key={c.id} value={c.id}>{c.name}</option>
        ))}
      </select>
      <button
        onClick={() => setCreating(true)}
        className="px-2 py-1.5 text-blue-600 text-sm hover:text-blue-800"
        title="Create new customer"
      >
        + New
      </button>
    </div>
  );
}
