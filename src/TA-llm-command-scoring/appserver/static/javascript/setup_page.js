"use strict";

require([
    "jquery",
    "splunkjs/splunk"
], function ($, splunkjs) {

    // === Constants and Namespaces === //
    const APP_NAME = "TA-llm-command-scoring";
    const APP_NAMESPACE = {
        owner: "nobody",
        app: APP_NAME,
        sharing: "global",
    };

    // === Utility Functions === //
    const getEl = id => document.getElementById(id);

    function maskApiKey(key) {
        if (!key || key.length < 3) return "n/a";
        return key.slice(0, 3) + "*".repeat(7);
    }

    function getSplunkService(namespace = APP_NAMESPACE) {
        const http = new splunkjs.SplunkWebHttp();
        return new splunkjs.Service(http, namespace);
    }

    async function setIsAppConfigured(service, val) {
        const configCollection = service.configurations(APP_NAMESPACE);
        await configCollection.fetch();

        const appConfig = configCollection.item('app');
        await appConfig.fetch();

        const installStanza = appConfig.item('install');
        await installStanza.fetch();
        await installStanza.update({ is_configured: val });
    }

    async function reloadApp(service) {
        const apps = service.apps();
        await apps.fetch();
        const app = apps.item(APP_NAME);
        await app.fetch();
        await app.reload();
    }

    function redirectToApp(waitMs = 500) {
        setTimeout(() => {
            window.location.href = `/app/${APP_NAME}`;
        }, waitMs);
    }

    function openModal(modal, form) {
        modal.style.display = "block";
        if (form) form.reset();
    }

    function closeModal(modal, form) {
        modal.style.display = "none";
        if (form) form.reset();
    }

    // === DOM Elements === //
    const modal = getEl('myModal');
    const addNewBut = getEl('addNewBut');
    const delSelBut = getEl('delSelectedBut');
    const closeButton = document.querySelector('.close-button');
    const cancelButton = getEl('cancelButton');
    const addCredForm = getEl('addCredForm');
    const credsTable = getEl('llm-creds-table');

    // === Modal Events === //
    addNewBut.onclick = () => openModal(modal, addCredForm);
    closeButton.onclick = () => closeModal(modal, addCredForm);
    cancelButton.onclick = () => closeModal(modal, addCredForm);
    window.onclick = event => {
        if (event.target === modal) closeModal(modal, addCredForm);
    };

    // === Credentials Listing === //
    async function renderCredentials() {
        try {
            const service = getSplunkService();
            const passwords = service.storagePasswords({ app: APP_NAME });
            await passwords.fetch();
            const list = passwords.list();

            // Clear table except the header (assumes <thead> used for header)
            $(credsTable).find("tbody").empty();

            list.forEach(pw => {
                const pwData = pw._properties;
                let credClearText = null;
                if (typeof pwData.clear_password === "string") {
                    try {
                        credClearText = JSON.parse(pwData.clear_password);
                    } catch (_) { }
                }
                if (!credClearText) return;

                const rowHtml = `
                    <tr>
                        <td>${pwData.username}</td>
                        <td>${credClearText.credDesc || "n/a"}</td>
                        <td>${credClearText.credLlmProv || "n/a"}</td>
                        <td>${credClearText.credModel || "n/a"}</td>
                        <td>${maskApiKey(credClearText.credApiKey)}</td>
                        <td class="action-cell">
                            <input type="checkbox" class="row-checkbox" />
                        </td>
                    </tr>
                `;
                $(credsTable).append(rowHtml);
            });
        } catch (err) {
            console.error("Error fetching passwords:", err);
        }
    }

    // Initial render of credentials when page loads
    $(document).ready(renderCredentials);

    // === Add Credential Handler === //
    addCredForm.onsubmit = async function (event) {
        event.preventDefault();

        // Collect and trim form fields
        const credName = getEl('credNameId').value.trim();
        const credNameClean = credName.replace(/\s+/g, '-').toLowerCase();
        const credDesc = getEl('credDescriptionId').value.trim();
        const credLlmProv = getEl('credLlmProviderId').value.trim();
        const credModel = getEl('credModelId').value.trim();
        const credApiKey = getEl('credApiSecretId').value.trim();

        // Basic field validation
        if (!credName) return alert("API Name can't be empty");
        if (!credLlmProv) return alert("API LLM Provider can't be empty");
        if (!credApiKey) return alert("API Key can't be empty");
        if (credApiKey.length < 6) return alert("The API Key is too short (min 6 characters)");

        const credPwToSave = {
            credNameClean,
            credDesc,
            credLlmProv,
            credModel,
            credApiKey,
        };

        try {
            const service = getSplunkService();

            // Save credentials
            const passKey = `${APP_NAME}:${credNameClean}:`;
            const passwords = service.storagePasswords(APP_NAMESPACE);
            await passwords.fetch();

            let existingPw = passwords.item(passKey);

            // Callback for credential save
            const onComplete = async (err) => {
                if (err) throw err;
                await setIsAppConfigured(service, 1);
                await reloadApp(service);
                redirectToApp();
            };

            if (!existingPw) {
                passwords.create({
                    name: credNameClean,
                    password: JSON.stringify(credPwToSave),
                    realm: APP_NAME,
                }, onComplete);
            } else {
                existingPw.update({
                    password: JSON.stringify(credPwToSave),
                }, onComplete);
            }
        } catch (e) {
            console.warn(e);
        }

        closeModal(modal, addCredForm);
    };

    // === Delete Selected Credentials Handler === //
    delSelBut.onclick = async () => {
        
        const checkedBoxes = document.querySelectorAll('#llm-creds-table .row-checkbox:checked');
        if (checkedBoxes.length === 0) {
            alert("No rows selected.");
            return;
        }

        const count = checkedBoxes.length;
        if (!confirm(`Are you sure you want to delete ${count} credential${count > 1 ? 's' : ''}?`)) return;

        const service = getSplunkService();
        const passwords = service.storagePasswords({ app: APP_NAME });
        await passwords.fetch();

        let anyDeleted = false;
        for (const checkbox of checkedBoxes) {
            const row = checkbox.closest("tr");
            const stanza = row.cells[0].textContent.trim();
            const passKey = `${APP_NAME}:${stanza}:`;
            const existingPw = passwords.item(passKey);
            if (!existingPw) continue;
            await existingPw.del();
            row.remove();
            anyDeleted = true;
        }
        if (anyDeleted) {
            await reloadApp(service);
            redirectToApp();
        }
    };

});