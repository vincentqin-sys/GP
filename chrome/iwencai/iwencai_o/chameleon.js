var TOKEN_SERVER_TIME_2 = new Date().getTime() / 1000;

class Cookie {
    constructor() {

    }

    getCookie() {
    }

    setCookie() {
        document.cookie = 'checkcookie=true'
    }

    delCookie() {
        document.cookie = 'checkcookie=; expires=Thu, 01 Jan 1970 00:00:00 GMT';
    }
}

class Base64 {
    constructor() {
        this.keys = {};
        let v = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_';
        for (let i = 0; i < v.length; i++) {
            this.keys[v[i]] = i;
        }
    }

    base64Encode() {

    }

    base64Decode(str) {
        let d = [];
        for (let i = 0; i < str.length; ) {
            let h = this.keys[str.charAt(i++)] << 18 | this.keys[str.charAt(i++)] << 12 | this.keys[str.charAt(i++)] << 6 | this.keys[str.charAt(i++)];
            d.push(h >> 16, h >> 8 & 0xff, h & 0xff);
        }
        console.log(d);
        return d;
    }

    encode() {

    }

    decode(str) {
        let t = this.base64Decode(str);
        if (t[0] != 3) {
            // error
            return 0;
        }
        let u = t[1];
        let rs = [];
        for (let j = 2, i = 0; j < t.length; ) {
            rs[i++] = t[j++] ^ u & 0xff;
            u = ~(u * 131);
        }
        console.log(rs);
        // check rs is OK
        let e = 0;
        for (let i = 0; i < rs.length; i++) {
            e = (e << 5) - e + rs[i];
        }
        e = e & 0xff;
        if (e == t[1]) {
            return rs;
        }
        return 0;
    }
}

new Base64().decode("A63p35jEtD6SpVDSFil9Uyc6vEIiCuHcaz5FsO-y6cSzZsO8t1rxrPuOVYF8")

class Build {
    constructor() {

    }

    init() {

    }

    update() {

    }
}