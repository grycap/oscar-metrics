import os

cluster_id = os.getenv("CLUSTER_ID")
# Configuration
folder_path = '/app/metrics'
assets_base_url = 'https://s3.amazonaws.com/metrics.oscar.grycap.net/assets'  # Local path to assets

OUT_PATH="/app/ui/"
INDEX="index.html"
# HTML template parts

html_header = f"""<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name='viewport' content='width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0'>
        <link href="{assets_base_url}/css/style.css" rel="stylesheet">
        <link rel="shortcut icon" href="{assets_base_url}/images/logo.png" type="image/webp">
        <link rel="apple-touch-icon" sizes="180x180" href="{assets_base_url}/images/logo.png">
        <link rel="icon" href="{assets_base_url}/images/favicon.png" type="image/webp">
        <title>OSCAR metrics</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;display=swap" rel="stylesheet">
    </head>
    <body>
        <div class="min-h-full flex-h-center" id="background_div">
            <input type="hidden" value="https://bio.link" id="app-url">
                <input type="hidden" value="null" id="is-featured">
                    <canvas id="bg-canvas" class="background-overlay"></canvas>
                </input>
            </input>

            <div class="mt-48 page-full-wrap relative ">
                <input type="hidden" value="creator-page" id="page-type">
                <img class="display-image m-auto" data-src="{assets_base_url}/images/logo.png" src="{assets_base_url}/images/logo.png" alt="OSCAR metrics"/>
                <h2 class="page-title page-text-color page-text-font mt-24 text-center text-fs-18">{cluster_id} metrics index"</h2>
                       
                <div class="mt-24">
"""

html_footer = """                </div>                                                                                
            </div>
        </div>
    </body>
</html>
"""
html_css = """

"""
html_file_entry_template = """                    <div class="page-item-wrap relative">
                        <div class="page-item flex-both-center absolute"></div>
                        <a target="_blank" class="page-item-each py-10 flex-both-center" href="{url}" data-id="{id}" data-type="page_item">
                            <img class="link-each-image" data-src="{icon}" src="{icon}" alt="{filename}"/>
                            <span class="item-title text-center">{filename}</span>
                        </a>
                    </div>
"""
# Determine the correct icon based on file type
def get_icon(file_name):
    if file_name.endswith('.html'):
        return f"{assets_base_url}/images/dashboard.png"
    elif file_name.endswith('.csv'):
        return f"{assets_base_url}/images/file.png"
    elif os.path.isdir(os.path.join(folder_path, file_name)):
        return f"{assets_base_url}/images/folder.png"
    else:
        return f"{assets_base_url}/images/file.png"

def generate_html(out_file, dir_path, out_url=''):
    # Generate HTML content
    html_content = html_header

    for i, file_name in enumerate(os.listdir(dir_path)):
        file_path = os.path.join(dir_path, file_name)
        if os.path.isfile(file_path) or os.path.isdir(file_path):
            if os.path.isdir(file_path):
                relative_url=file_name+".html"
                generate_html(OUT_PATH+relative_url, file_path, out_url+file_name+"/")
                file_url = relative_url
            else:
                file_url = out_url+file_name
            icon = get_icon(file_name)
            if "dashboard" in file_name:
                file_name = "GoAccess Dashboard"
            if "goaccess-metrics" in file_name:
                file_name = "GoAccess Metrics"
            if "prometheus-metrics" in file_name:
                file_name = "Prometheus Metrics" 
            file_entry = html_file_entry_template.format(url=file_url, id=i, icon=icon, filename=file_name)
            html_content += file_entry

    html_content += html_footer

    # Write the generated HTML to a file
    with open(out_file, 'w') as f:
        f.write(html_content)

    print(f"HTML file '{out_file}' has been generated.")
    # Upload to s3



def main():
    generate_html(OUT_PATH+INDEX, folder_path)

if __name__ == "__main__":
    main()