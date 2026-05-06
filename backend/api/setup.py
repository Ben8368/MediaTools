"""Router registration helpers for the FastAPI application."""

from __future__ import annotations

from fastapi import FastAPI


def configure_application_routes(
    app: FastAPI,
    *,
    job_registry,
    run_simple_job,
    get_file_manager,
    get_current_workspace,
    set_current_workspace,
    get_auditor_status,
    get_auditor_config,
    run_auditor_scan_once,
    save_auditor_config,
    get_wechat_moments_draft,
    get_wechat_moments_status,
    save_wechat_moments_draft,
    export_wechat_moments_image,
    get_photoshop_status,
    scan_photoshop_document,
    list_photoshop_tickets,
    get_photoshop_ticket,
    save_photoshop_ticket,
    start_ticket_execution,
    get_photoshop_execution_state,
    cancel_photoshop_execution,
    get_preview_generator,
    get_preview_max_bytes,
    extract_icon,
    resolve_allowed_path,
    run_fetch_batch_stream,
    run_transcode_job,
    run_decrypt_job,
    result_success,
    asset_library_cls,
    get_asset_scan_max_files,
    list_workspace_media,
    analyze_subtitle_for_workbench,
    export_clips_from_workbench,
):
    from backend.api.routes.adobe import create_router as create_adobe_router
    from backend.api.routes.assets import create_router as create_assets_router
    from backend.api.routes.auditor import create_router as create_auditor_router
    from backend.api.routes.browser import router as browser_router
    from backend.api.routes.filebrowser import router as filebrowser_router
    from backend.api.routes.files import create_router as create_files_router
    from backend.api.routes.log import router as log_router
    from backend.api.routes.media import create_router as create_media_router
    from backend.api.routes.path_picker import router as path_picker_router
    from backend.api.routes.photoshop import create_router as create_photoshop_router
    from backend.api.routes.system import create_router as create_system_router
    from backend.api.routes.task_center import router as task_center_router
    from backend.api.routes.wechat import create_router as create_wechat_router
    from backend.api.routes.workbench import create_router as create_workbench_router
    from backend.api.routes.workspace import create_router as create_workspace_router
    from backend.services.log_buffer import install_log_buffer

    app.include_router(create_system_router(get_current_workspace, get_auditor_status, get_wechat_moments_status))
    app.include_router(
        create_wechat_router(
            get_current_workspace,
            get_wechat_moments_draft,
            get_wechat_moments_status,
            save_wechat_moments_draft,
            export_wechat_moments_image,
        )
    )
    app.include_router(
        create_auditor_router(
            run_simple_job,
            get_current_workspace,
            get_auditor_config,
            get_auditor_status,
            run_auditor_scan_once,
            save_auditor_config,
        )
    )
    app.include_router(
        create_photoshop_router(
            job_registry,
            get_current_workspace,
            get_photoshop_status,
            scan_photoshop_document,
            list_photoshop_tickets,
            get_photoshop_ticket,
            save_photoshop_ticket,
            start_ticket_execution,
            get_photoshop_execution_state,
            cancel_photoshop_execution,
        )
    )
    app.include_router(create_adobe_router(job_registry, get_current_workspace, get_photoshop_status))
    app.include_router(
        create_files_router(
            get_file_manager,
            get_current_workspace,
            get_preview_generator,
            get_preview_max_bytes,
            extract_icon,
        )
    )
    app.include_router(
        create_media_router(
            job_registry,
            get_current_workspace,
            resolve_allowed_path,
            run_fetch_batch_stream,
            run_transcode_job,
            run_decrypt_job,
            result_success,
        )
    )
    app.include_router(
        create_assets_router(
            get_current_workspace,
            resolve_allowed_path,
            asset_library_cls,
            get_asset_scan_max_files,
        )
    )
    app.include_router(create_workspace_router(get_current_workspace, set_current_workspace))
    app.include_router(path_picker_router)
    app.include_router(create_workbench_router(run_simple_job, list_workspace_media, analyze_subtitle_for_workbench, export_clips_from_workbench))
    app.include_router(filebrowser_router)
    app.include_router(task_center_router)

    app.include_router(browser_router)

    install_log_buffer()
    app.include_router(log_router)
