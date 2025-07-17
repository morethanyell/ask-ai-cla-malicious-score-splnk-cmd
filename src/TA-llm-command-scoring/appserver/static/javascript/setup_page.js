"use strict";

const appName = "TA-llm-command-scoring";
const appNamespace = {
    owner: "nobody",
    app: appName,
    sharing: "global",
};

// Splunk Web Framework Provided files
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

            list.forEach(pw => {

                const credName = pw.name;
                const credNameClean = credName.match(/.+\:(.+)\:/)[1]
                const credClearText = JSON.parse(pw.)
                const credLlmProv = credClearText.credLlmProv;
                const credModel = credClearText.credModel;
                const credApiKey = credClearText.credApiKey;

                const row = `
                    <tr>
                        <td>${credNameClean}</td>
                        <td>${credLlmProv}</td>
                        <td>${credModel}</td>
                        <td>${credApiKey}</td>
                        <td class="action-cell"><span class="ellipsis">&#8942;</span></td>
                    </tr>
                `;

                $('#llm-creds-table').append(row);

            });

        } catch (err) {
            console.error("Error fetching passwords:", err);
        }
    })

    // Handle form submission
    addCredForm.onsubmit = async function (event) {
        event.preventDefault();

        const credName = document.getElementById('credNameId').value;
        const credNameClean = credName.trim().replace(/\s+/g, '-').toLowerCase();
        const credLlmProv = document.getElementById('credLlmProviderId').value;
        const credModel = document.getElementById('credModelId').value;
        const credApiKey = document.getElementById('credApiSecretId').value;
        const credPwToSave = {
            credNameClean: credNameClean,
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

                if (!credName) {
                    throw new Error('API key is empty!');
                }

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

        modal.style.display = 'none'; // Close the modal after submission
        addCredForm.reset(); // Reset the form after submission
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
