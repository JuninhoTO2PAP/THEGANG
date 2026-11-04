/** Espelho das permissões do backend. */

export const Perm = {
  VIEW_CHANNELS: 1 << 0,
  SEND_MESSAGES: 1 << 1,
  MANAGE_CHANNELS: 1 << 2,
  MANAGE_ROLES: 1 << 3,
  MANAGE_GROUP: 1 << 4,
  CONNECT_VOICE: 1 << 5,
  KICK_MEMBERS: 1 << 6,
  START_EVENTS: 1 << 7,
  ADMINISTRATOR: 1 << 30,
};

export const PERM_OPTIONS = [
  {
    flag: Perm.VIEW_CHANNELS,
    label: "Ver canais",
    help: "Enxerga a lista de canais do grupo.",
  },
  {
    flag: Perm.SEND_MESSAGES,
    label: "Enviar mensagens",
    help: "Pode falar nos canais de texto.",
  },
  {
    flag: Perm.CONNECT_VOICE,
    label: "Conectar na voz",
    help: "Entra em salas de call / LiveKit.",
  },
  {
    flag: Perm.MANAGE_CHANNELS,
    label: "Gerenciar canais",
    help: "Cria e organiza canais de texto e voz.",
  },
  {
    flag: Perm.MANAGE_ROLES,
    label: "Gerenciar cargos",
    help: "Cria cargos e atribui a membros.",
  },
  {
    flag: Perm.MANAGE_GROUP,
    label: "Gerenciar grupo",
    help: "Edita o grupo e gera convites.",
  },
  {
    flag: Perm.KICK_MEMBERS,
    label: "Expulsar membros",
    help: "Remove pessoas do grupo (quando ativo).",
  },
  {
    flag: Perm.START_EVENTS,
    label: "Iniciar eventos (CPT)",
    help: "Inicia Diário, Intensivo e Campeonato na call.",
  },
  {
    flag: Perm.ADMINISTRATOR,
    label: "Administrador",
    help: "Poder total — ignora as outras permissões.",
  },
];

export function can(permissions, flag) {
  const value = Number(permissions) || 0;
  if (value & Perm.ADMINISTRATOR) return true;
  return Boolean(value & flag);
}
