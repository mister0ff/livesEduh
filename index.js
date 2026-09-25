const { TikTokLiveConnection, WebcastEvent } = require('tiktok-live-connector');
const firebase = require('firebase/compat/app');
require('firebase/compat/database');

// Configuração corrigida para apontar para o projeto "jogos-468c5"
const firebaseConfig = {
  apiKey: "AIzaSyD7e_jzxdwysOWzZ8RgUDYZsH2Wd6U9Tv8",
  authDomain: "jogos-468c5.firebaseapp.com",
  databaseURL: "https://jogos-468c5-default-rtdb.firebaseio.com",
  projectId: "jogos-468c5",
  storageBucket: "jogos-468c5.firebasestorage.app",
  messagingSenderId: "707655679439",
  appId: "1:707655679439:web:4090d4f9f453e8769d66ba",
  measurementId: "G-02Q9MZ50DX"
};

firebase.initializeApp(firebaseConfig);
const db = firebase.database();

const tiktokUsername = "dearjuc";
const connection = new TikTokLiveConnection(tiktokUsername, {});

const curtidasRegistradas = new Set();

function extrairUsuario(data) {
    const nome =
        data.uniqueId ||
        data.user?.uniqueId ||
        data.nickname ||
        data.user?.nickname ||
        null;

    const avatar =
        data.profilePictureUrl ||
        data.user?.profilePicture?.urls?.[0] ||
        data.user?.avatarThumb?.urlList?.[0] ||
        null;

    return { nome, avatar };
}

connection.connect().then(state => {
    console.log(`✅ Conectado com sucesso na live da sala: ${state.roomId}`);
}).catch(err => {
    console.error('❌ Erro ao conectar. Certifique-se de estar ao vivo:', err.message || err);
});

connection.on(WebcastEvent.FOLLOW, data => {
    const { nome, avatar } = extrairUsuario(data);
    if (!nome) { console.log('⚠️ FOLLOW sem nome identificado'); return; }
    console.log(`👤 Novo seguidor: ${nome}`);
    db.ref('eventos/').push({ tipo: 'follow', nome, avatar: avatar || null });
});

connection.on(WebcastEvent.LIKE, data => {
    const { nome, avatar } = extrairUsuario(data);
    console.log(`❤️ ${nome || '(sem nome)'} curtiu a live`);

    if (!nome) return;
    if (!curtidasRegistradas.has(nome)) {
        curtidasRegistradas.add(nome);
        db.ref('eventos/').push({ tipo: 'like', nome, avatar: avatar || null });
    }
});

connection.on(WebcastEvent.GIFT, data => {
    if (data.giftType === 1 && !data.repeatEnd) return;
    const { nome, avatar } = extrairUsuario(data);
    if (!nome) return;

    const valor = (data.diamondCount || 1) * (data.repeatCount || 1);
    console.log(`🎁 ${nome} enviou presente (${valor} diamantes)`);

    db.ref('eventos/').push({
        tipo: 'gift', nome, avatar: avatar || null, valor, presente: data.giftName || null
    });
});

connection.on(WebcastEvent.CHAT, data => {
    const { nome, avatar } = extrairUsuario(data);
    if (!nome) return;

    const textoCompleto = data.comment || '';
    const primeiraLetra = textoCompleto.trim().charAt(0);

    if (!primeiraLetra) return;

    console.log(`💬 ${nome} comentou ${primeiraLetra}`);

    db.ref('eventos/').push({
        tipo: 'chat',
        nome,
        avatar: avatar || null,
        comentario: primeiraLetra
    });
});

connection.on(WebcastEvent.DISCONNECTED, () => {
    console.log('⚠️ Desconectado da live.');
});

connection.on('error', err => {
    console.error('Erro na conexão:', err);
});
