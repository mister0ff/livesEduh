const { WebcastPushConnection } = require('tiktok-live-connector');
const firebase = require('firebase/compat/app');
require('firebase/compat/database');

// Suas credenciais do Firebase
const firebaseConfig = {
    apiKey: "SUA_API_KEY",
    databaseURL: "SUA_DATABASE_URL",
    projectId: "SEU_PROJECT_ID"
};

firebase.initializeApp(firebaseConfig);
const db = firebase.database();

// SEU @ DO TIKTOK AQUI
const tiktokUsername = "SEU_USUARIO_DO_TIKTOK";
const tiktokLiveConnection = new WebcastPushConnection(tiktokUsername);

tiktokLiveConnection.connect().then(state => {
    console.log(`Conectado com sucesso na live da sala: ${state.roomId}`);
}).catch(err => {
    console.error('Erro ao conectar na live. Certifique-se de estar ao vivo!', err);
});

// Evento disparado quando alguém te SEGUE
tiktokLiveConnection.on('follow', data => {
    console.log(`Novo seguidor: ${data.uniqueId}`);
    
    // Envia para o Firebase
    db.ref('seguidores/').push({
        nome: data.uniqueId,
        avatar: data.profilePictureUrl
    });
});

