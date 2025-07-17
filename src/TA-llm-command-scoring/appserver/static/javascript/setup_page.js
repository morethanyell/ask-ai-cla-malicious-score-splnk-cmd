"use strict";

const appName = "TA-llm-command-scoring";
const appNamespace = {
    owner: "nobody",
    app: appName,
    sharing: "global",
};

require([
    "jquery", "splunkjs/splunk",
], function ($, splunkjs) {

    const modal = document.getElementById('myModal');
    const addNewBut = document.getElementById('addNewBut');
    const closeButton = document.querySelector('.close-button');
    const cancelButton = document.getElementById('cancelButton');
    const addCredForm = document.getElementById('addCredForm');

    addNewBut.onclick = function () {
        modal.style.display = 'block';
    }

    closeButton.onclick = function () {
        modal.style.display = 'none';
        addCredForm.reset();
    }

    cancelButton.onclick = function () {
        modal.style.display = 'none';
        addCredForm.reset();
        console.log('Pop-up cancelled.');
    }

    window.onclick = function (event) {
        if (event.target == modal) {
            modal.style.display = 'none';
            addCredForm.reset();
        }
    }

    $(document).ready(async function () {

        try {

            const http = new splunkjs.SplunkWebHttp();
            const service = new splunkjs.Service(http, appNamespace);

            const passwords = service.storagePasswords({ app: appName });
            await passwords.fetch();

            const list = passwords.list();

            for (const pw of list) {

                pwData = pw._properties;

                const credName = pwData.username;
                let credClearText = null;

                if (typeof pwData.clear_password === "string") {
                    try {
                        credClearText = JSON.parse(pwData.clear_password);
                    } catch (_) { }
                }

                if (!credClearText) continue;

                const credDesc = credClearText.credDesc ?? "n/a";
                const credLlmProv = credClearText.credLlmProv ?? "n/a";
                const credModel = credClearText.credModel ?? "n/a";
                const credApiKey = credClearText.credApiKey ?? "n/a";
                const credApiKeyMasked = (credApiKey.slice(0, 3) + "*".repeat(7)) ?? "n/a";

                const row = `
                    <tr>
                        <td>${credName}</td>
                        <td>${credDesc}</td>
                        <td>${credLlmProv}</td>
                        <td>${credModel}</td>
                        <td>${credApiKeyMasked}</td>
                        <td class="action-cell"><span class="ellipsis">&#8942;</span></td>
                    </tr>
                `;

                $('#llm-creds-table').append(row);

            }

        } catch (err) {
            console.error("Error fetching passwords:", err);
        }
    });

    // Handle form submission
    addCredForm.onsubmit = async function (event) {

        event.preventDefault();

        const credName = document.getElementById('credNameId').value;
        const credNameClean = credName.trim().replace(/\s+/g, '-').toLowerCase();
        const credDesc = document.getElementById('credDescriptionId').value;
        const credLlmProv = document.getElementById('credLlmProviderId').value;
        const credModel = document.getElementById('credModelId').value;
        const credApiKey = document.getElementById('credApiSecretId').value;

        const fields = {
            credName: "API Name",
            credLlmProv: "API LLM Provider",
            credApiKey: "API Key"
        };

        for (const [key, value] of Object.entries(fields)) {
            if (!eval(key)) {
                alert(`${value} can't be empty`);
                throw new Error(`${value} is empty!`);
            }
        }

        const credPwToSave = {
            credNameClean: credNameClean,
            credDesc: credDesc,
            credLlmProv: credLlmProv,
            credModel: credModel,
            credApiKey, credApiKey
        }

        try {

            const http = new splunkjs.SplunkWebHttp();
            const service = new splunkjs.Service(
                http,
                appNamespace,
            );

            const configCollection = service.configurations(appNamespace);
            await configCollection.fetch();

            const appConfig = configCollection.item('app');
            await appConfig.fetch();

            const installStanza = appConfig.item('install');
            await installStanza.fetch();

            const isConfigured = installStanza.properties().is_configured;
            if (isTrue(isConfigured)) {
                console.warn(`App is configured already (is_configured=${isConfigured}), skipping setup page...`);
                reloadApp(service);
                redirectToApp();
            }

            const passKey = `${appName}:${credNameClean}:`;
            const passwords = service.storagePasswords(appNamespace);
            await passwords.fetch();

            const existingPw = passwords.item(passKey);
            await existingPw;

            function passwordCallback(err, resp) {

                if (err) throw err;

                setIsConfigured(installStanza, 1);
                reloadApp(service);

                $('.success').show();
                redirectToApp();

            } if (!existingPw) {

                passwords.create(
                    {
                        name: credNameClean,
                        password: JSON.stringify(credPwToSave),
                        realm: appName,
                    }, passwordCallback);

            } else {
                existingPw.update(
                    {
                        password: credApiKey,
                    }, passwordCallback)
            }

        } catch (e) {
            console.warn(e);
            $('.error').show();
            $('#error_details').show();
            const errText = `Error encountered while saving credentials.`;
            errText += (e.toString() === '[object Object]') ? '' : e.toString();
            if (e.hasOwnProperty('status')) errText += `<br>[${e.status}] `;
            if (e.hasOwnProperty('responseText')) errText += e.responseText;
            $('#error_details').html(errText);
        }

        modal.style.display = 'none';
        addCredForm.reset();

    }

    async function setIsConfigured(installStanza, val) {
        await installStanza.update({
            is_configured: val
        });
    }

    async function reloadApp(service) {
        var apps = service.apps();
        await apps.fetch();

        var app = apps.item(appName);
        await app.fetch();
        await app.reload();
    }

    function redirectToApp(waitMs) {
        setTimeout(() => {
            window.location.href = `/app/${appName}`;
        }, 800);
    }

    function isTrue(v) {
        if (typeof (v) === typeof (true)) return v;
        if (typeof (v) === typeof (1)) return v !== 0;
        if (typeof (v) === typeof ('true')) {
            if (v.toLowerCase() === 'true') return true;
            if (v === 't') return true;
            if (v === '1') return true;
        }
        return false;
    }

});
