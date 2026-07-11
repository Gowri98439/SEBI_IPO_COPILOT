import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { ScrollText, CheckCircle, XCircle, Info } from 'lucide-react';
import api from '../api/client';

interface AuditEvent {
  id: string;
  action: string;
  action_category: string;
  details: string;
  ip_address: string;
  status: string;
  created_at: string;
}

const CATEGORY_COLORS: Record<string, string> = {
  AUTH:      'badge-accent',
  DOCUMENT:  'badge-neutral',
  COMPLIANCE:'badge-warning',
  DRHP:      'badge-accent',
  EXPORT:    'badge-neutral',
  VALIDATION:'badge-neutral',
  DEFAULT:   'badge-neutral',
};

const AuditLogPage: React.FC = () => {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!workspaceId) return;
    api.get(`/workspaces/${workspaceId}/audit-logs`)
      .then((data: any) => setEvents(Array.isArray(data) ? data : []))
      .catch(() => setEvents([]))
      .finally(() => setLoading(false));
  }, [workspaceId]);

  if (loading) return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem' }}>
      <div className="spinner" style={{ width: '36px', height: '36px' }} />
    </div>
  );

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <ScrollText size={24} color="var(--accent)" />
          Audit Trail
        </h1>
        <p className="page-subtitle">
          Immutable record of all workspace activity — logged per SEBI compliance requirements
        </p>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>
            Activity Log
            <span style={{ marginLeft: '0.625rem', fontSize: '0.8125rem', fontWeight: 500, color: 'var(--text-muted)' }}>
              ({events.length} events)
            </span>
          </h2>
        </div>

        {events.length > 0 ? (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Action</th>
                  <th>Category</th>
                  <th>Details</th>
                  <th>IP Address</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {events.map((evt) => (
                  <tr key={evt.id}>
                    <td style={{ whiteSpace: 'nowrap', fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                      {new Date(evt.created_at).toLocaleString('en-IN', {
                        day: '2-digit', month: 'short', year: 'numeric',
                        hour: '2-digit', minute: '2-digit',
                      })}
                    </td>
                    <td style={{ fontWeight: 500, fontSize: '0.875rem', fontFamily: 'var(--font-mono)' }}>
                      {evt.action}
                    </td>
                    <td>
                      <span className={`badge ${CATEGORY_COLORS[evt.action_category] ?? CATEGORY_COLORS.DEFAULT}`}>
                        {evt.action_category}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', maxWidth: '280px' }}>
                      {evt.details}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                      {evt.ip_address || 'N/A'}
                    </td>
                    <td>
                      {evt.status === 'SUCCESS' ? (
                        <span className="badge badge-success">
                          <CheckCircle size={11} strokeWidth={2.5} /> Success
                        </span>
                      ) : (
                        <span className="badge badge-danger">
                          <XCircle size={11} strokeWidth={2.5} /> {evt.status}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ padding: '4rem 2rem', textAlign: 'center' }}>
            <Info size={36} color="#CBD5E1" strokeWidth={1.5} style={{ marginBottom: '1rem' }} />
            <p style={{ margin: 0, fontWeight: 600, color: 'var(--text-primary)' }}>No activity recorded yet</p>
            <p style={{ margin: '0.375rem 0 0', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
              All workspace actions will appear here automatically.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default AuditLogPage;
