function randomString
{
    param([int] $count);
    return -join ((48..57) + (97..122) | Get-Random -Count $count | % {[char]$_})
}



function getRandArrField
{
    param([String[]] $array)
        return $array[(Get-Random -Maximum ([array]$array).count)]
}

function randomDir
{
    param([string] $dst)

        New-Item -ItemType directory -Path "$dst\$(randomString $(Get-Random -Minimum 10 -Maximum 50))"

}

function populateDirectory
{
    Param(

            [String]
            $Dest,

            [String[]]
            $End

         )

        $rand_1 = (Get-Random -Minimum 25 -Maximum 50)
        for ($i=0; $i -le $rand_1 ; $i++ )
        {
            $rand_dir = $(randomDir $Dest)

            $rand_2 = (Get-Random -Minimum 10 -Maximum 20)
            for ($b=0; $b -le $rand_2; $b++ )
            {
                $f_path = "$rand_dir\$(randomString(Get-Random -Minimum 2 -Maximum 10)).$(getRandArrField $End)"
                # Write-Host "Generating file: $f_path"
                $out = new-object byte[] (Get-Random -Maximum 148576 -Minimum 1024 ); (new-object Random).NextBytes($out); [IO.File]::WriteAllBytes($f_path, $out)

            }

            $f_path = "$Dest\$(randomString(Get-Random -Minimum 2 -Maximum 10)).$(getRandArrField $End)"
            # Write-Host "Generating file: $f_path"
            $out = new-object byte[] (Get-Random -Maximum 148576 -Minimum 1024 ); (new-object Random).NextBytes($out); [IO.File]::WriteAllBytes($f_path, $out)

        }
}

function make-link-dir ($target, $link) {
    Write-Host "Creating link: $target -> $link"
    cmd /c mklink /D `"$link`" `"$target`"
}

function make-link-file ($target, $link) {
    Write-Host "Creating link: $target -> $link"
    cmd /c mklink `"$link`" `"$target`"
}

[String[]] $audio_extensions = @(
        "mp3",
        "ogg",
        "flv",
        "wav",
        "webm"
        )
populateDirectory "$($HOME)\Music" $audio_extensions

[String[]] $video_extensions = @(
        "avi",
        "flv",
        "mov",
        "mpg",
        "wmv"
        )
populateDirectory "$($HOME)\Videos" $video_extensions


[String[]] $3d_extensions = @(
        "cad",
        "3d",
        "3dl",
        "dwg",
        "hcl"
        )
populateDirectory "$($HOME)\Documents" $3d_extensions


[String[]] $office_extensions = @(
        "dot",
        "odt",
        "obd",
        "vml",
        "pdf"
        )
populateDirectory "$($HOME)\Documents" $office_extensions


[String[]] $picture_extensions = @(
        "png",
        "jpg",
        "raw",
        "vml",
        "bmp",
        "gif"
        )
populateDirectory "$($HOME)\Pictures" $picture_extensions


# Add random links to favorite
foreach ( $folder in  (Get-ChildItem -Path "$env:HOMEPATH\Documents") )
{
    # Write-Host "Folder: " $folder.FullName

    if((Get-Item $folder.FullName) -is [System.IO.DirectoryInfo])
    {
        if((Get-Random -Minimum 0 -Maximum 100) -ge 90 )
        {
            make-link-dir $folder.FullName "$($env:HOMEDRIVE)$($env:HOMEPATH)\Links\$($folder.Name)"
        }

        if((Get-Random -Minimum 0 -Maximum 100) -ge 90 )
        {
            make-link-dir $folder.FullName "$($env:HOMEDRIVE)$($env:HOMEPATH)\Desktop\$($folder.Name)"
        }
    }

    if((Get-Item $folder.FullName) -is [System.IO.FileInfo])
    {
        if((Get-Random -Minimum 0 -Maximum 100) -ge 90 )
        {
            make-link-file $folder.FullName "$($env:HOMEDRIVE)$($env:HOMEPATH)\Links\$($folder.Name)"
        }

        if((Get-Random -Minimum 0 -Maximum 100) -ge 90 )
        {
            make-link-file $folder.FullName "$($env:HOMEDRIVE)$($env:HOMEPATH)\Desktop\$($folder.Name)"
        }
    }
}
