import type { AppMessages } from "./en-US.ts";

export const ptBRMessages: AppMessages = {
  common: {
    appName: "MangAI",
    brandNote: "Workspace IA-first para localizacao de manga e quadrinhos.",
    localeSwitcherLabel: "Idioma da interface",
  },
  home: {
    eyebrow: "Pipeline de localizacao IA-first",
    title: "Limpe, traduza e diagramme paginas com controle humano.",
    subtitle:
      "O MangAI mantem cada etapa editavel, da revisao de regioes e mascaras de limpeza ate o mapeamento das falas e exportacoes prontas para PSD.",
    primaryAction: "Revisar fluxo",
    secondaryAction: "Inspecionar base",
    foundationTitle: "Base atual",
    foundationCopy:
      "O monorepo ja possui contratos compartilhados, uma base de API testada e primitivas de frontend com locale para ingles e portugues.",
    foundationItems: [
      {
        label: "Schema compartilhado",
        value: "Pronto",
        description:
          "Entidades do projeto, regras de locale e contratos de jobs vivem em um unico pacote TypeScript.",
      },
      {
        label: "Base da API",
        value: "Testada",
        description:
          "Rotas FastAPI, configuracoes e validacao de requisicao ja estao cobertas por testes automatizados.",
      },
      {
        label: "Locales da UI",
        value: "Ativos",
        description:
          "A interface agora resolve locales suportados, serve catalogos tipados e rejeita entradas invalidas com seguranca.",
      },
    ],
    workflowTitle: "Caminho de execucao",
    workflowCopy:
      "O primeiro slice do produto segue o plano de arquitetura: estabelecer a casca, congelar contratos e adicionar fluxos uma capacidade por vez.",
    workflowItems: [
      {
        step: "01",
        title: "Enviar e inspecionar",
        description:
          "Criar um projeto, ingerir paginas e expor cada asset detectado como objeto de primeira classe com estados de ciclo de vida definidos.",
      },
      {
        step: "02",
        title: "Limpar a arte",
        description:
          "Revisar mascaras, comparar variantes de limpeza e manter a arte original acessivel para acabamento preciso no Photoshop.",
      },
      {
        step: "03",
        title: "Traduzir e mapear falas",
        description:
          "Importar roteiro ou OCR, associar cada linha a regiao correta e manter o loop de revisao rapido e auditavel.",
      },
      {
        step: "04",
        title: "Diagramar e exportar",
        description:
          "Posicionar texto com presets de estilo, preservar editabilidade e entregar PSD, JPG e PDF a partir de um unico estado de projeto.",
      },
    ],
    deliveryTitle: "Por que este slice importa",
    deliveryCopy:
      "Esta base de frontend e intencionalmente enxuta: ela prova roteamento, i18n, contratos compartilhados e confiabilidade de build antes das interacoes pesadas do editor.",
    deliveryItems: [
      {
        step: "A",
        title: "Locale previsivel",
        description:
          "Cada locale suportado e explicito, tipado e validado contra o pacote compartilhado de contratos.",
      },
      {
        step: "B",
        title: "Shell Next.js buildavel",
        description:
          "O web app agora sobe como um projeto App Router real em vez de um diretorio placeholder.",
      },
      {
        step: "C",
        title: "Progresso guiado por testes",
        description:
          "Helpers de frontend sao verificados com testes automatizados, e o build do web app faz parte da validacao.",
      },
      {
        step: "D",
        title: "Proximos passos mais seguros",
        description:
          "Os proximos slices podem focar em dashboard, uploads e interacoes do editor sem reescrever a base.",
      },
    ],
    milestoneNote:
      "Marco atual: shell web online, locales ativos, contratos compartilhados e validacao automatizada pronta.",
    defaultWorkspaceLabel: "Locale padrao do workspace",
  },
};
