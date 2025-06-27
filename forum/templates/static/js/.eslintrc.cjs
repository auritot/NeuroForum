// .eslintrc.cjs
module.exports = {
    env: {
        browser: true,
        node: true,
        es2021: true,
    },
    parserOptions: {
        ecmaVersion: 12,
        sourceType: 'module',
    },
    plugins: ['no-unsanitized', 'security', 'security-node'],
    extends: [
        'eslint:recommended',
        'plugin:security/recommended',
        'plugin:security-node/recommended',
    ],
    rules: {
        'no-unsanitized/method': 'error',
        'no-unsanitized/property': 'error'
    }
};
