import {defineConfig} from 'wxt'
export default defineConfig({
  manifest: {
    name: 'Club Lab · lector local', description: 'Actualización local del club al abrir Club Lab; lectura visible, sin contraseñas ni operaciones de mercado.',
    permissions: ['activeTab', 'scripting', 'storage', 'sidePanel'],
    // Chrome grants the EA host; code restricts execution to the official Web App path.
    // No accounts.ea.com, cookies, debugger, history or remote server permissions.
    host_permissions: ['http://localhost/*', 'http://127.0.0.1/*', 'https://www.ea.com/*'],
    action: {default_title: 'Abrir Club Lab'},
    side_panel: {default_path: 'sidepanel.html'},
  },
})
