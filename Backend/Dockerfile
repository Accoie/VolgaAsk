FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /code
COPY *.csproj ./
RUN dotnet restore
COPY . .
RUN dotnet publish -c Release --no-restore -o /out

FROM mcr.microsoft.com/dotnet/aspnet:8.0
WORKDIR /app
COPY --from=build /out .
RUN mkdir -p /app/keys && chown app:app /app/keys
USER app
ENTRYPOINT ["dotnet", "VolgaAsk.Api.dll"]
