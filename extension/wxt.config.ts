import {defineConfig} from 'wxt'
export default defineConfig({
  manifest: {
    name: 'Club Lab · lector revisable', description: 'Inspector guiado de regiones visibles y lector de muestras. Perfiles EA pendientes de contraste.',
    permissions: ['activeTab', 'scripting', 'storage', 'sidePanel'],
    // Transport to the user's existing backend only. No EA host permission.
    host_permissions: ['http://localhost/*', 'http://127.0.0.1/*'],
    action: {default_title: 'Abrir Club Lab'},
    side_panel: {default_path: 'sidepanel.html'},
  },
})
